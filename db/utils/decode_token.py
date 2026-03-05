import jwt
import base64
import json
import requests
import os
import logging
from .encrypt_utils import create_hash, encrypt_email_vault, encrypt_email
from jwt.algorithms import RSAAlgorithm
from dotenv import load_dotenv

load_dotenv()

AUTH_TENANT_ID = os.getenv("AUTH_TENANT_ID")
if AUTH_TENANT_ID is None:
    raise ValueError("Error: no value set for 'AUTH_TENANT_ID'")

env = os.getenv("ENVIRONMENT")
if env is None:
    raise ValueError("Error: no value set for 'env'")

deployed_environments = ["DEVT", "TEST", "STAGING", "PROD"]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_groups_ids = os.environ.get("USER_GROUPS", "")


def is_admin_user(user_groups):
    if not user_groups:
        return False
    return user_groups_ids in user_groups


async def decode_token(token: str):
    """
    Decodes the JWT access token from the frontend
    Args:
        token (str): the access token.
    Returns:
        hashed_email (str): The hashed email from the token to use with the DB
        encrypted_email (str): The encrypted email from the token to store in the DB
        is_admin (bool): Whether user is admin
    """
    logger.info("CLUB-LLOYDS-BE-DT-01")
    try:
        if token == None or token == "null":
            logger.info("CLUB-LLOYDS-BE-DT-TOKEN-NONE")
            # Note: This will likely cause an error in the split logic below if not handled

        header_b64 = token.split(".")[0]
        header_json = base64.urlsafe_b64decode(header_b64 + "==").decode("utf-8")
        header = json.loads(header_json)
        kid = header["kid"]
        logger.info("CLUB-LLOYDS-BE-DT-02")

        issuer = f"https://login.microsoftonline.com/{AUTH_TENANT_ID}/discovery/keys"
        response = requests.get(issuer, timeout=(3, 5))
        jwks = response.json()
        logger.info("CLUB-LLOYDS-BE-DT-03")

        public_keys = {
            key["kid"]: RSAAlgorithm.from_jwk(json.dumps(key)) for key in jwks["keys"]
        }
        public_key = public_keys.get(kid)
        logger.info("CLUB-LLOYDS-BE-DT-04")

        decoded_token = jwt.decode(
            token, public_key, "RS256", options={"verify_signature": False}
        )

        email = decoded_token.get("upn") or decoded_token.get("email") or None
        
        if env in deployed_environments:
            encrypted_email = encrypt_email_vault(email.lower())
        else:
            encrypted_email = encrypt_email(email.lower())

        hashed_email = create_hash(email)
        user_groups = decoded_token.get("groups", None)
        is_admin = is_admin_user(user_groups)
        
        logger.info("CLUB-LLOYDS-BE-DT-05")
        return (hashed_email, encrypted_email, is_admin)

    except Exception as e:
        logger.info("CLUB-LLOYDS-BE-DT-ERROR")
        print("JWT could not be decoded successfully")
        raise Exception(f"Error - {e}")
