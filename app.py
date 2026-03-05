import logging
import signal
import time
import asyncio
import os
from prisma import Prisma
from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from waitress import serve

from functions.searchresponse import generate_response
from functions.modifyresponse import (
    summarise_response,
    elaborate_response,
    generate_follow_up_qs,
)
from modules.club_lloyds_config import ClubLloydsConfig
from modules.error_handler import register_error_handlers
from db.utils.posting_utils import handle_request
from db.post_feedback import post_feedback
from db.get_messages import get_messages, get_messages_with_feedback
from db.utils.decode_token import decode_token

# Logging Setup
logging.basicConfig(level=logging.INFO)
logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# App Initialization
is_ready = False
app = Flask(__name__)
logger.info("CLUB-LLOYDS-BE-APP-00")

config = ClubLloydsConfig("config.yaml")
cors = CORS()
cors.init_app(app)
db = Prisma()
env = os.environ.get("ENVIRONMENT", "development")
logger.info(f"ENVIRONMENT: {env}")

# Signal Handling
def handle_sigterm(signal, frame):
    global is_ready
    is_ready = False
    time.sleep(5)
    print("Graceful shutdown complete")
    exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
register_error_handlers(app)

# Health & Probe Endpoints
@app.route("/readiness")
def readiness_probe():
    if is_ready:
        return jsonify({"status": "ready"}), 200
    else:
        logger.warning("CLUB-LLOYDS-BE-APP-11")
        return jsonify({"status": "not ready"}), 503

@app.route("/liveness")
def liveness_probe():
    return jsonify({"status": "alive"}), 200

@app.route("/health")
def healthcheck():
    logger.info("CLUB-LLOYDS-BE-APP-13")
    response = make_response("healthcheck", 200)
    response.mimetype = "text/plain"
    return response

@app.route("/health/db")
def check_db_health():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(connect_and_check())
        if result:
            return jsonify({"status": "success", "message": "Connected to Database"}), 200
        else:
            return jsonify({"status": "error", "message": "Could not connect"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

async def connect_and_check():
    try:
        await db.connect()
        await db.disconnect()
        return True
    except Exception:
        return False

# User Endpoints
@app.route("/user-groups", methods=["POST"])
async def get_user_group():
    access_token = request.headers.get("x-access-token", None)
    *_, is_admin = await decode_token(access_token)
    return {"is_admin_user": is_admin}

# Core Query Endpoints
@app.route("/query", methods=["POST"])
async def query():
    logger.info("CLUB-LLOYDS-BE-APP-02")
    data = request.get_json()
    question = data["query"]
    chat_history = data.get("chat_history", [])
    
    answer, citations, default_response = generate_response(
        question, chat_history, config, location=None
    )
    
    logger.info("CLUB-LLOYDS-BE-APP-03")
    message_id = await handle_request(
        request, chat_history[-1] if chat_history else {}, question, answer, citations, "Query"
    )
    return {
        "answer": answer,
        "citations": citations,
        "id": message_id,
        "default_response": default_response,
    }

@app.route("/summarise", methods=["POST"])
async def summarise():
    logger.info("CLUB-LLOYDS-BE-APP-04")
    prev_chat = request.get_json()["prev_chat"]
    summarised_answer = summarise_response(prev_chat["question"], prev_chat["answer"], config)
    
    message_id = await handle_request(
        request, prev_chat, "Summarise", summarised_answer, [], "Summarise"
    )
    return {
        "summarised_answer": summarised_answer,
        "id": message_id,
        "citations": prev_chat["citations"],
    }

@app.route("/elaborate", methods=["POST"])
async def elaborate():
    logger.info("CLUB-LLOYDS-BE-APP-06")
    prev_chat = request.get_json()["prev_chat"]
    elaborated_answer = elaborate_response(
        prev_chat["question"], prev_chat["answer"], prev_chat["citations"], config
    )
    
    message_id = await handle_request(
        request, prev_chat, "Elaborate", elaborated_answer, [], "Elaborate"
    )
    return {
        "elaborated_answer": elaborated_answer,
        "id": message_id,
        "citations": prev_chat["citations"],
    }

@app.route("/followup", methods=["POST"])
async def followup():
    logger.info("CLUB-LLOYDS-BE-APP-08")
    prev_chat = request.get_json()["prev_chat"]
    follow_up_qs = generate_follow_up_qs(
        prev_chat["question"], prev_chat["answer"], prev_chat["citations"], config
    )
    
    message_id = await handle_request(
        request, prev_chat, "Generate related follow-up questions", follow_up_qs, [], "Follow Up"
    )
    return {"follow_up_qs": follow_up_qs, "id": message_id}

@app.route("/feedback", methods=["POST"])
async def feedback():
    logger.info("CLUB-LLOYDS-BE-APP-14")
    access_token = request.headers.get("x-access-token", None)
    hashed_email, *_ = await decode_token(access_token)
    
    data = request.get_json()
    feedback_id = await post_feedback(
        data["id"], data["message"], data["types"], data["is_response_useful"], hashed_email
    )
    return {"id": feedback_id}

@app.route("/messages", methods=["POST"])
async def messages():
    logger.info("CLUB-LLOYDS-BE-APP-15")
    access_token = request.headers.get("x-access-token", None)
    hashed_email, *_ = await decode_token(access_token)
    
    data = request.get_json()
    messages_list, total_pages = await get_messages(
        hashed_email, data["start_date"], data["end_date"], data["page"]
    )
    return {"data": messages_list, "total_pages": total_pages}

@app.route("/get-messages-feedback", methods=["POST"])
async def messages_feedback():
    logger.info("CLUB-LLOYDS-BE-APP-GMF")
    access_token = request.headers.get("x-access-token", None)
    *_, is_admin = await decode_token(access_token)
    
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    messages_list, total_pages, total_count = await get_messages_with_feedback(
        data["start_date"], data["end_date"], data["page"], data.get("feedback_types")
    )
    return {"data": messages_list, "total_pages": total_pages, "total_count": total_count}

if __name__ == "__main__":
    is_ready = True
    serve(app, host="0.0.0.0", port=5002)
