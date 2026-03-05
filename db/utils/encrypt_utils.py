import hashlib
import logging
import os
from base64 import b64encode
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
from credential import load_default_azure_credential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_hash(string: str) -> str:
    """Creates a deterministic 64 character hash of a string"""
    normalized = str(string).encode("utf-8")
    hash_object = hashlib.sha256(normalized)
    return hash_object.hexdigest()


def encrypt_email(email: str) -> str:
    """Encrypts the email using AES-256-CBC (for local development)"""
    logger.info("CLUB-LLOYDS-BE-EE-01")
    SECRET_KEY = os.environ.get("EMAIL_ENCRYPTION_KEY")
    if not SECRET_KEY:
        raise ValueError("EMAIL_ENCRYPTION_KEY environment variable is not set")
    
    KEY = hashlib.sha256(SECRET_KEY.encode()).digest()
    IV = b"0123456789abcdef"
    backend = default_backend()
    
    cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV), backend=backend)
    encryptor = cipher.encryptor()
    
    logger.info("CLUB-LLOYDS-BE-EE-02")
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(email.encode()) + padder.finalize()
    
    logger.info("CLUB-LLOYDS-BE-EE-03")
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    
    logger.info("CLUB-LLOYDS-BE-EE-04")
    return b64encode(encrypted).decode("utf-8")


def encrypt_email_vault(email: str) -> str:
    """Encrypts the email using Azure Key Vault"""
    logger.info("CLUB-LLOYDS-BE-EEV-01")
    key_vault_url = os.environ.get("KEY_VAULT_URL")
    key_name = os.environ.get("KEY_NAME")
    
    if not key_vault_url and not key_name:
        logger.info("CLUB-LLOYDS-BE-EEV-VAR-ERROR")
        raise ValueError("KEY_VAULT_URL and KEY_NAME environment variable is not set")
    
    logger.info("CLUB-LLOYDS-BE-EEV-02")
    encryption_algorithm = EncryptionAlgorithm.rsa_oaep
    
    try:
        credential = load_default_azure_credential()
        logger.info("CLUB-LLOYDS-BE-EEV-03")
        key_id = f"{key_vault_url}/keys/{key_name}"
        
        logger.info("CLUB-LLOYDS-BE-EEV-04")
        crypto_client = CryptographyClient(key_id, credential)
        
        logger.info("CLUB-LLOYDS-BE-EEV-05")
        plain_text_bytes = email.encode("utf-8")
        encrypt_result = crypto_client.encrypt(encryption_algorithm, plain_text_bytes)
        
        logger.info("CLUB-LLOYDS-BE-EEV-06")
        ciphertext_bytes = encrypt_result.ciphertext
        encrypted_string_b64 = b64encode(ciphertext_bytes).decode("utf-8")
        
        logger.info("CLUB-LLOYDS-BE-EEV-07")
        return encrypted_string_b64
        
    except Exception as e:
        logger.info("CLUB-LLOYDS-BE-EEV-EXCEPTION")
        logger.error(f"An error occurred during encryption - {e}")
        raise
