import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException
from prisma.errors import PrismaError
from .errors import AzureOpenAIError

logger = logging.getLogger(__name__)

class FeedbackError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def handle_http_exception(error):
    logger.info("CLUB-LLOYDS-BE-ERR-07")
    return (
        jsonify({
            "error": error.name,
            "message": error.description,
        }),
        error.code,
    )

def handle_prisma_error(error):
    logger.error("Prisma error occurred: %s", error)
    logger.info("CLUB-LLOYDS-BE-ERR-06")
    return (
        jsonify({
            "error": "Database Error",
            "message": str(error),
        }),
        500,
    )

def handle_azure_openai_error(error: AzureOpenAIError):
    return jsonify(error.to_dict()), error.status_code

def handle_generic_exception(error):
    logger.error("Unexpected error: %s", error)
    logger.info("CLUB-LLOYDS-BE-ERR-05")
    return (
        jsonify({
            "error": "Internal Server Error",
            "message": str(error),
        }),
        500,
    )

def handle_feedback_error(error: FeedbackError):
    logger.info("CLUB-LLOYDS-BE-ERR-08")
    return (
        jsonify({
            "error": "Feedback Error",
            "message": error.message,
        }),
        error.status_code,
    )

def register_error_handlers(app):
    app.register_error_handler(HTTPException, handle_http_exception)
    app.register_error_handler(PrismaError, handle_prisma_error)
    app.register_error_handler(AzureOpenAIError, handle_azure_openai_error)
    app.register_error_handler(FeedbackError, handle_feedback_error)
    app.register_error_handler(Exception, handle_generic_exception)
