"""
Morpho routes dependencies - to avoid circular imports
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from web3 import Web3, HTTPProvider
from eth_account import Account

# Database connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'vault_wallet')
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]

# Web3 connection - Load from dotenv if needed
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

ALCHEMY_API_KEY = os.environ.get('ALCHEMY_API_KEY')
if not ALCHEMY_API_KEY:
    raise ValueError("ALCHEMY_API_KEY not found in environment")

w3 = Web3(HTTPProvider(f'https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}'))

# Direct private key access (NO FERNET)
def get_owner_private_key() -> str:
    """Get owner private key directly from environment"""
    private_key = os.environ.get("OWNER_PRIVATE_KEY") or os.environ.get("USER_WALLET_PRIVATE_KEY")
    if not private_key:
        raise ValueError("OWNER_PRIVATE_KEY not found in environment")
    # Remove 0x prefix if present
    if private_key.startswith('0x'):
        private_key = private_key[2:]
    return private_key

def decrypt_private_key(encrypted_key: bytes) -> str:
    """Get private key directly (no decryption needed)"""
    # If it's stored as bytes, decode it
    if isinstance(encrypted_key, bytes):
        return encrypted_key.decode()
    return encrypted_key

