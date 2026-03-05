import logging

from prisma import Prisma

from db.utils.posting_utils import get_feedback_options_ids
from modules.error_handler import FeedbackError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def post_feedback(
    message_id: int,
    feedback_free_text: str,
    feedback_types: list,
    is_response_useful: bool,
    hashed_email: str,
):
    """Posts feedback given a request from the frontend"""
    db = Prisma()
    await db.connect()
    logger.info("CLUB-LLOYDS-BE-PF-01: Connected to DB")

    user = await db.users.find_first(where={"unique_identifier": hashed_email})
    if not user:
        logger.info("CLUB-LLOYDS-BE-PF-USER-02: User not found")
        await db.disconnect()
        raise FeedbackError("User not found.", 403)

    logger.info(f"CLUB-LLOYDS-BE-PF-USER-03: Found user {user.id}")

    message = await db.message.find_unique(where={"id": message_id})
    if not message:
        logger.info("CLUB-LLOYDS-BE-PF-MSG-01: Message not found")
        await db.disconnect()
        raise FeedbackError("Message not found.", 400)

    logger.info(f"CLUB-LLOYDS-BE-PF-MSG-02: Found message {message.id}")

    session = await db.session.find_unique(where={"id": message.session_id})
    if not session or session.user_id != user.id:
        logger.info("CLUB-LLOYDS-BE-PF-SESSION-01: Session not found or user mismatch")
        await db.disconnect()
        raise FeedbackError("You can only give feedback for your own messages.", 403)

    logger.info(f"CLUB-LLOYDS-BE-PF-SESSION-02: Session verified for user {session.user_id}")

    existing_feedback = await db.feedback.find_first(where={"message_id": message_id})
    if existing_feedback:
        logger.info("CLUB-LLOYDS-BE-PF-FB-01: Feedback already exists for this message")
        await db.disconnect()
        raise FeedbackError("Feedback already submitted for this message.", 403)

    logger.info("CLUB-LLOYDS-BE-PF-FB-02: No existing feedback for this message")

    feedback_options_ids = await get_feedback_options_ids(db, feedback_types)
    logger.info(f"CLUB-LLOYDS-BE-PF-OPT-01: Feedback options IDs: {feedback_options_ids}")

    try:
        async with db.tx() as transaction:
            feedback_response = await transaction.feedback.create(
                data={
                    "feedback_free_text": feedback_free_text,
                    "message_id": message_id,
                    "is_response_useful": is_response_useful,
                }
            )
            logger.info(f"CLUB-LLOYDS-BE-PF-02: Feedback created with ID {feedback_response.id}")
            
            feedback_id = feedback_response.id
            for ft in feedback_options_ids:
                await transaction.selectedfeedbackoptions.create(
                    data={"feedback_id": feedback_id, "feedback_options_id": ft}
                )
                logger.info(f"CLUB-LLOYDS-BE-PF-OPT-02: Feedback option {ft} linked to feedback {feedback_id}")

            logger.info("CLUB-LLOYDS-BE-PF-03: All feedback options linked")
            return feedback_id
    finally:
        logger.info("CLUB-LLOYDS-BE-PF-04: Disconnected from DB")
        await db.disconnect()
