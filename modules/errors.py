import logging

UNKNOWN_ERROR_MESSAGE = """An unknown error occurred. Please try again."""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureOpenAIError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv


def handle_openai_error(error):
    body = error.body
    if "message" in body:
        error_message = body["message"]
    else:
        error_message = UNKNOWN_ERROR_MESSAGE

    if "status" in body:
        error_code = body["status"]
    elif "code" in body:
        error_code = body["code"]
    elif "statusCode" in body:
        error_code = body["statusCode"]
    else:
        error_code = 500

    if error_code == 400 and "response was filtered" in error_message:
        error_code = 422

    if error_code == "context_length_exceeded":
        error_code = 508
        error_message = (
            "An unexpected error occurred (token limit reached). "
            "Ask the user to rephrase the question and try again."
        )

    if isinstance(error_code, str):
        try:
            error_code = int(error_code)
        except ValueError:
            error_code = 500

    logger.info("CLUB-LLOYDS-BE-ERR-01")
    raise AzureOpenAIError(error_message, error_code) from error


def handle_other_error(error):
    error_description = str(error)

    if "414" in error_description:
        message = (
            "This model's maximum context length is 16385 tokens. "
            "However, your messages exceeded this limit. "
            "Please reduce the length of the message."
        )
        logger.info("CLUB-LLOYDS-BE-ERR-02")
        raise AzureOpenAIError(message, 414) from error

    if "403" in error_description:
        message = (
            "Unauthorized. Access token is missing, invalid, audience is incorrect "
            "(https://cognitiveservices.azure.com), or have expired."
        )
        logger.info("CLUB-LLOYDS-BE-ERR-03")
        raise AzureOpenAIError(message, 401) from error

    error_msg = UNKNOWN_ERROR_MESSAGE + " " + error_description
    logger.info("CLUB-LLOYDS-BE-ERR-04")
    raise AzureOpenAIError(error_msg, 500) from error
