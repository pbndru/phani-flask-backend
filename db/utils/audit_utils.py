import logging
from prisma import Prisma
from db.utils.posting_utils import create_or_retrieve_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def audit_download(hashed_email, encrypted_email, message_data):
    """Ensure user exists, then insert a DownloadAudit record"""
    db = Prisma()
    await db.connect()
    
    logger.info("CLUB-LLOYDS-BE-AD-01")
    try:
        user = await db.users.find_unique(where={"unique_identifier": hashed_email})
        logger.info("CLUB-LLOYDS-BE-AD-02")
        
        if not user:
            logger.info("CLUB-LLOYDS-BE-AD-03")
            user = await create_or_retrieve_user(db, hashed_email, encrypted_email)
            
        logger.info("CLUB-LLOYDS-BE-AD-04")
        downloadaudit = await db.downloadaudit.create(
            data={
                "user_id": user.id,
                "filtered_start_date": message_data.get("start_date"),
                "filtered_end_date": message_data.get("end_date"),
            }
        )
        
        logger.info("CLUB-LLOYDS-BE-AD-05")
        return downloadaudit
        
    finally:
        await db.disconnect()
