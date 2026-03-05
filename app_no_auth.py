import logging
import os
from flask import Flask, request, make_response, jsonify
from flask_cors import CORS

from functions.searchresponse import generate_response
from functions.modifyresponse import (
    summarise_response,
    elaborate_response,
    generate_follow_up_qs,
)
from modules.club_lloyds_config import ClubLloydsConfig

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)
logger.info("CLUB-LLOYDS-SIMPLE-APP-START")

# Load Configuration
config = ClubLloydsConfig("config.yaml")
cors = CORS()
cors.init_app(app)

@app.route("/health")
def healthcheck():
    logger.info("Health check")
    response = make_response("healthcheck", 200)
    response.mimetype = "text/plain"
    return response

@app.route("/query", methods=["POST"])
def query():
    """Simple query endpoint without authentication or database"""
    logger.info("Processing query")
    try:
        data = request.get_json()
        question = data.get("query", "")
        chat_history = data.get("chat_history", [])

        if not question:
            return jsonify({"error": "No query provided"}), 400

        answer, citations, default_response = generate_response(
            question, chat_history, config, location=None
        )
        
        logger.info(f"Generated answer with {len(citations)} citations")
        return jsonify({
            "answer": answer,
            "citations": citations,
            "default_response": default_response,
        })
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/summarise", methods=["POST"])
def summarise():
    """Summarise a previous response"""
    logger.info("Processing summarise request")
    try:
        data = request.get_json()
        prev_chat = data.get("prev_chat", {})
        prev_question = prev_chat.get("question", "")
        prev_answer = prev_chat.get("answer", "")

        if not prev_question or not prev_answer:
            return jsonify({"error": "Missing previous question or answer"}), 400

        summarised_answer = summarise_response(prev_question, prev_answer, config)
        return jsonify({
            "summarised_answer": summarised_answer,
            "citations": prev_chat.get("citations", []),
        })
    except Exception as e:
        logger.error(f"Error processing summarise: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/elaborate", methods=["POST"])
def elaborate():
    """Elaborate on a previous response"""
    logger.info("Processing elaborate request")
    try:
        data = request.get_json()
        prev_chat = data.get("prev_chat", {})
        prev_question = prev_chat.get("question", "")
        prev_answer = prev_chat.get("answer", "")
        prev_context = prev_chat.get("citations", [])

        if not prev_question or not prev_answer:
            return jsonify({"error": "Missing previous question or answer"}), 400

        elaborated_answer = elaborate_response(
            prev_question, prev_answer, prev_context, config
        )
        return jsonify({
            "elaborated_answer": elaborated_answer,
            "citations": prev_context,
        })
    except Exception as e:
        logger.error(f"Error processing elaborate: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/followup", methods=["POST"])
def followup():
    """Generate follow-up questions"""
    logger.info("Processing follow-up request")
    try:
        data = request.get_json()
        prev_chat = data.get("prev_chat", {})
        prev_question = prev_chat.get("question", "")
        prev_answer = prev_chat.get("answer", "")
        prev_context = prev_chat.get("citations", [])

        if not prev_question or not prev_answer:
            return jsonify({"error": "Missing previous question or answer"}), 400

        follow_up_qs = generate_follow_up_qs(
            prev_question, prev_answer, prev_context, config
        )
        return jsonify({"follow_up_qs": follow_up_qs})
    except Exception as e:
        logger.error(f"Error processing follow-up: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    logger.info(f"Starting simple development server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
