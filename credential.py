import logging
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_default_azure_credential():
    """
    Instantiates and returns the DefaultAzureCredential for 
    authenticating with Azure services like Key Vault.
    """
    try:
        credential = DefaultAzureCredential()
        return credential
    except Exception as e:
        logger.error(f"Error instantiating credential: {e}")
        return None
