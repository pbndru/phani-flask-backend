import os
import signal
import time
import logging
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv
from waitress import serve

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
cors = CORS()
cors.init_app(app)

# Environment
env = os.environ.get("ENVIRONMENT", "LOCAL")
logger.info(f"Environment: {env}")

# Readiness flag
is_ready = False

# Graceful shutdown handler
def handle_sigterm(signum, frame):
    global is_ready
    logger.info("SIGTERM received, starting graceful shutdown...")
    is_ready = False
    time.sleep(5)
    logger.info("Graceful shutdown complete")
    exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

# Health check endpoints
@app.route("/health")
def healthcheck():
    logger.info("Health check")
    response = make_response("healthy", 200)
    response.mimetype = "text/plain"
    return response

@app.route("/readiness")
def readiness_probe():
    if is_ready:
        return jsonify({"status": "ready"}), 200
    else:
        return jsonify({"status": "not ready"}), 503

@app.route("/liveness")
def liveness_probe():
    return jsonify({"status": "alive"}), 200

# Query endpoint
@app.route("/query", methods=["POST"])
async def query():
    logger.info("Query received")
    if request.method == "POST":
        data = request.get_json()
        question = data.get("query", "")
        
        # TODO: Implement RAG pipeline for Club Lloyds docs
        answer = f"Echo: {question}"
        
        return jsonify({
            "answer": answer,
            "citations": [],
            "id": "test-123"
        })

if __name__ == "__main__":
    HOST_IP = "0.0.0.0"
    PORT = 5001
    THREADS = int(os.environ.get("THREADS", 100))
    is_ready = True
    
    logger.info("Mini-Backend starting...")
    
    if env == "LOCAL":
        # Development mode using Flask's built-in server
        app.run(host=HOST_IP, port=PORT, debug=True)
    else:
        # Production mode using the Waitress WSGI server
        # Learn more at the [Waitress Documentation](https://docs.pylonsproject.org)
        serve(app, host=HOST_IP, port=PORT, threads=THREADS)
