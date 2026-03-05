import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from prisma import Prisma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_date_range(start_date_str: str, end_date_str: str) -> tuple[datetime, datetime]:
    start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
    end_date += timedelta(days=1)
    return start_date, end_date


async def get_messages(
    hashed_email: str, start_date: datetime, end_date: datetime, page: int, size: int = 10
):
    """Get messages given a request from the frontend"""
    db = Prisma()
    await db.connect()
    logger.info("CLUB-LLOYDS-BE-GM-01")

    try:
        user = await db.users.find_unique(where={"unique_identifier": hashed_email})
        if not user:
            return [], 0

        logger.info("CLUB-LLOYDS-BE-GM-02")
        page_size = size
        start_date, adjusted_end_date = normalize_date_range(start_date, end_date)

        base_query = {
            "session": {"user_id": user.id},
            "created_at": {"gte": start_date, "lt": adjusted_end_date},
            "requestType": {"is_active": True},
            "messageType": {"is_active": True},
        }

        query_options = {
            "where": base_query,
            "order": {"created_at": "desc"},
            "include": {
                "messageCitations": True,
            },
        }

        skip = (page - 1) * page_size
        query_options["take"] = page_size
        query_options["skip"] = skip

        message_links = await db.message.find_many(**query_options)
        logger.info("CLUB-LLOYDS-BE-GM-03")

        total_count = await db.message.count(where=base_query)
        logger.info("CLUB-LLOYDS-BE-GM-04")

        total_pages = math.ceil(total_count / page_size)
        results = []

        for msg in message_links:
            source_links = [
                {"title": c.title, "url": c.url, "chunks": c.source_extracts}
                for c in msg.messageCitations
            ]
            results.append(
                {
                    "id": msg.id,
                    "question": msg.question,
                    "answer": msg.response,
                    "previous_chat_history": msg.previous_chat_history,
                    "created_at": msg.created_at,
                    "citations": source_links,
                }
            )
        return results, total_pages

    finally:
        logger.info("CLUB-LLOYDS-BE-GM-05")
        await db.disconnect()


async def stream_messages_in_batches(hashed_email, start_date, end_date):
    """Async generator that yields messages in chunks from DB"""
    page = 1
    size = 500
    while True:
        messages, total_pages = await get_messages(
            hashed_email, start_date, end_date, page, size
        )
        if not messages:
            break
        yield messages
        page += 1
        if page > total_pages:
            break


async def get_messages_with_feedback(
    start_date: datetime,
    end_date: datetime,
    page: int,
    feedback_types: Optional[List[str]] = None,
    size: int = 10,
):
    """Get messages with feedback information"""
    db = Prisma()
    await db.connect()
    logger.info("CLUB-LLOYDS-BE-GMF-01")

    try:
        page_size = size
        start_date, adjusted_end_date = normalize_date_range(start_date, end_date)

        base_query = {
            "created_at": {"gte": start_date, "lt": adjusted_end_date},
            "requestType": {"is_active": True},
            "messageType": {"is_active": True},
        }

        final_where = base_query
        if feedback_types:
            types_norm = {str(t).strip().lower() for t in feedback_types if t is not None}
            or_disjunction = []

            if "true" in types_norm:
                or_disjunction.append({"feedback": {"some": {"is_response_useful": True}}})
            if "false" in types_norm:
                or_disjunction.append({"feedback": {"some": {"is_response_useful": False}}})
            if "none" in types_norm:
                or_disjunction.append({"feedback": {"none": {}}})

            if or_disjunction:
                final_where = {"AND": [base_query, {"OR": or_disjunction}]}

        total_count = await db.message.count(where=final_where)
        if total_count == 0:
            return [], 0, 0

        total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
        effective_page = page if total_pages and 1 <= page <= total_pages else 1
        skip = (effective_page - 1) * page_size

        query_options = {
            "where": final_where,
            "order": {"created_at": "desc"},
            "include": {
                "messageCitations": True,
                "feedback": True,
            },
            "take": page_size,
            "skip": skip,
        }

        message_links = await db.message.find_many(**query_options)

        feedback_ids: List[int] = [
            fb.id for msg in message_links for fb in (getattr(msg, "feedback", []) or [])
        ]

        options_by_feedback_id: dict[int, List[str]] = defaultdict(list)
        if feedback_ids:
            sfo_rows = await db.selectedfeedbackoptions.find_many(
                where={"feedback_id": {"in": feedback_ids}},
                include={"feedbackOptions": True},
            )
            for row in sfo_rows:
                opt = getattr(row, "feedbackOptions", None)
                name = getattr(opt, "name", None) if opt else None
                if name:
                    options_by_feedback_id[row.feedback_id].append(name)

        results = []
        for msg in message_links:
            source_links = [
                {"title": c.title, "url": c.url, "chunks": c.source_extracts}
                for c in msg.messageCitations
            ]
            fb = getattr(msg, "feedback", []) or []
            feedback_data = None
            if fb:
                fb_item = fb[0]
                selected_options = options_by_feedback_id.get(fb_item.id, [])
                feedback_data = {
                    "id": fb_item.id,
                    "feedback_text": fb_item.feedback_free_text,
                    "is_response_useful": fb_item.is_response_useful,
                    "created_at": fb_item.created_at,
                    "selected_options": selected_options,
                }

            results.append(
                {
                    "id": msg.id,
                    "question": msg.question,
                    "answer": msg.response,
                    "previous_chat_history": msg.previous_chat_history,
                    "created_at": msg.created_at,
                    "citations": source_links,
                    "feedback": feedback_data,
                }
            )
        return results, total_pages, total_count

    finally:
        logger.info("CLUB-LLOYDS-BE-GMF-04")
        await db.disconnect()
