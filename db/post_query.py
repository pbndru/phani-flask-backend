import json
import logging

from db.utils.posting_utils import (
    create_or_retrieve_user,
    get_data_source_id,
    get_message_types,
    get_request_type_id,
    parse_response,
    transform_citations,
)
from prisma import Prisma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def post_query(
    query: str,
    chat_history: dict,
    hashed_email: str,
    encrypted_email: str,
    response: any,
    citations: any,
    request_type: str,
    session_id: str,
):
    """Creates or uses existing user details to post a query to the database"""
    db = Prisma()
    await db.connect()
    logger.info("CLUB-LLOYDS-BE-PQ-01")

    user_record = await create_or_retrieve_user(db, hashed_email, encrypted_email)
    request_type_id = await get_request_type_id(db, request_type)
    non_error_type_id, _ = await get_message_types(db)
    data_source_id = await get_data_source_id(db, "Club Lloyds")

    logger.info("CLUB-LLOYDS-BE-PQ-02")

    MAX_RETRIES = 1
    retries = 0

    while retries < MAX_RETRIES:
        try:
            async with db.tx() as transaction:
                await transaction.session.upsert(
                    where={"id": session_id},
                    data={
                        "create": {"id": session_id, "user_id": user_record.id},
                        "update": {},
                    },
                )
                logger.info("CLUB-LLOYDS-BE-PQ-03")

                message_post_response = await transaction.message.create(
                    data={
                        "question": query,
                        "response": parse_response(response),
                        "previous_chat_history": (
                            json.dumps(chat_history) if chat_history else "{}"
                        ),
                        "request_type_id": request_type_id,
                        "message_type_id": non_error_type_id,
                        "data_source_id": data_source_id,
                        "session_id": session_id,
                    }
                )
                logger.info("CLUB-LLOYDS-BE-PQ-04")

                if len(citations) > 0:
                    transformed_citations = transform_citations(
                        citations, message_post_response.id
                    )
                    await transaction.messagecitations.create_many(
                        data=transformed_citations
                    )
                    logger.info("CLUB-LLOYDS-BE-PQ-05")

                logger.info("CLUB-LLOYDS-BE-PQ-06")
                return message_post_response.id

        except Exception as e:
            logger.error("CLUB-LLOYDS-BE-PQ-ERROR")
            logger.error(f"Failed to post to database - {e}")
            if retries < MAX_RETRIES:
                retries += 1
                logger.info("CLUB-LLOYDS-BE-PQ-RETRY")
                continue
            else:
                return None
        finally:
            logger.info("CLUB-LLOYDS-BE-PQ-07")
            await db.disconnect()
