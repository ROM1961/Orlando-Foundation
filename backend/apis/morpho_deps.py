"""
Morpho routes dependencies - to avoid circular imports
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from web3 import Web3, HTTPProvider
from cryptography.fernet import Fernet

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

# Decryption
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

def decrypt_private_key(encrypted_key: bytes) -> str:
    """Decrypt private key"""
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    decrypted = cipher_suite.decrypt(encrypted_key)
    return decrypted.decode()
