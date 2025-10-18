from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncpg
from passlib.context import CryptContext
import jwt
from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
import json
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# PostgreSQL connection
DATABASE_URL = f"postgresql://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}@{os.environ['PGHOST']}/{os.environ['PGDATABASE']}?sslmode={os.environ['PGSSLMODE']}"

# Web3 setup
ALCHEMY_URL = f"https://eth-mainnet.g.alchemy.com/v2/{os.environ['ALCHEMY_API_KEY']}"
w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))

# Encryption setup
cipher_suite = Fernet(base64.urlsafe_b64encode(bytes.fromhex(os.environ['ENCRYPTION_KEY'])))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Database connection pool
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    logging.info("Database pool created")

@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool:
        await pool.close()
        logging.info("Database pool closed")

# Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str

class CreateVault(BaseModel):
    label: str
    vault_type: str = "multi-sig"
    required_signatures: int = 2
    owner_addresses: List[str]

class SendTransaction(BaseModel):
    vault_id: str
    to_address: str
    amount: float
    token: str = "ETH"

class VaultBalance(BaseModel):
    vault_address: str
    eth_balance: float
    eth_usd: float
    acs_balance: float
    acs_usd: float
    total_usd: float

class Transaction(BaseModel):
    id: str
    vault_id: str
    tx_hash: str
    action: str
    amount: float
    token: str
    status: str
    timestamp: datetime

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=int(os.environ.get('JWT_EXPIRATION_HOURS', 24)))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, os.environ['JWT_SECRET'], algorithm=os.environ['JWT_ALGORITHM'])

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, os.environ['JWT_SECRET'], algorithms=[os.environ['JWT_ALGORITHM']])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def encrypt_private_key(private_key: str) -> bytes:
    return cipher_suite.encrypt(private_key.encode())

def decrypt_private_key(encrypted_key: bytes) -> str:
    return cipher_suite.decrypt(encrypted_key).decode()

async def get_eth_price() -> float:
    """Get ETH price from Chainlink price feed"""
    try:
        price_feed_abi = [{"inputs":[],"name":"latestAnswer","outputs":[{"internalType":"int256","name":"","type":"int256"}],"stateMutability":"view","type":"function"}]
        contract = w3.eth.contract(address=os.environ['PRICE_FEED'], abi=price_feed_abi)
        price = contract.functions.latestAnswer().call()
        return price / 10**8  # Chainlink returns price with 8 decimals
    except Exception as e:
        logging.error(f"Error fetching ETH price: {e}")
        return 3500.0  # Fallback price

async def get_acs_price() -> float:
    """Get ACS token price (mock for now)"""
    return 1.25  # Mock price

# Auth endpoints
@api_router.post("/auth/register", response_model=Token)
async def register(user: UserRegister):
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1 OR username = $2", user.email, user.username)
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create user
        user_id = str(uuid.uuid4())
        hashed_pwd = hash_password(user.password)
        await conn.execute(
            "INSERT INTO users (id, username, email, password_hash) VALUES ($1, $2, $3, $4)",
            user_id, user.username, user.email, hashed_pwd
        )
        
        # Generate token
        access_token = create_access_token({"sub": user_id})
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user_id,
            username=user.username
        )

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id, username, password_hash FROM users WHERE email = $1", credentials.email)
        if not user or not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user_id = str(user['id'])
        access_token = create_access_token({"sub": user_id})
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user_id,
            username=user['username']
        )

# Vault endpoints
@api_router.post("/vaults/create")
async def create_vault(vault: CreateVault, user_id: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        # Create new Ethereum account for the vault
        account = Account.create()
        vault_address = account.address
        encrypted_key = encrypt_private_key(account.key.hex())
        
        vault_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO user_vaults (id, user_id, vault_address, owner_addresses, network, vault_type, label, private_key_encrypted)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, vault_id, user_id, vault_address, vault.owner_addresses, 'ethereum', vault.vault_type, vault.label, encrypted_key)
        
        return {
            "vault_id": vault_id,
            "vault_address": vault_address,
            "label": vault.label,
            "owner_addresses": vault.owner_addresses
        }

@api_router.get("/vaults")
async def get_vaults(user_id: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        vaults = await conn.fetch("SELECT id, vault_address, label, vault_type, owner_addresses, created_at FROM user_vaults WHERE user_id = $1 ORDER BY created_at DESC", user_id)
        return [{"id": v['id'], "vault_address": v['vault_address'], "label": v['label'], "vault_type": v['vault_type'], "owner_addresses": v['owner_addresses'], "created_at": v['created_at'].isoformat()} for v in vaults]

@api_router.get("/vaults/{vault_id}/balance")
async def get_vault_balance(vault_id: str, user_id: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        vault = await conn.fetchrow("SELECT vault_address FROM user_vaults WHERE id = $1 AND user_id = $2", vault_id, user_id)
        if not vault:
            raise HTTPException(status_code=404, detail="Vault not found")
        
        vault_address = vault['vault_address']
        
        # Get ETH balance
        eth_balance_wei = w3.eth.get_balance(vault_address)
        eth_balance = float(w3.from_wei(eth_balance_wei, 'ether'))
        
        # Get prices
        eth_price = await get_eth_price()
        acs_price = await get_acs_price()
        
        # Get ACS token balance (mock for now)
        acs_balance = 1000.0  # Mock balance
        
        eth_usd = eth_balance * eth_price
        acs_usd = acs_balance * acs_price
        
        return VaultBalance(
            vault_address=vault_address,
            eth_balance=eth_balance,
            eth_usd=eth_usd,
            acs_balance=acs_balance,
            acs_usd=acs_usd,
            total_usd=eth_usd + acs_usd
        )

@api_router.post("/vaults/{vault_id}/send")
async def send_transaction(vault_id: str, tx: SendTransaction, user_id: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        vault = await conn.fetchrow("SELECT vault_address, private_key_encrypted FROM user_vaults WHERE id = $1 AND user_id = $2", vault_id, user_id)
        if not vault:
            raise HTTPException(status_code=404, detail="Vault not found")
        
        # Decrypt private key
        private_key = decrypt_private_key(vault['private_key_encrypted'])
        account = Account.from_key(private_key)
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(vault['vault_address'])
        amount_wei = w3.to_wei(tx.amount, 'ether')
        
        transaction = {
            'nonce': nonce,
            'to': tx.to_address,
            'value': amount_wei,
            'gas': 21000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 1  # Mainnet
        }
        
        # Sign and send
        signed = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        
        # Store transaction
        tx_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO vault_transactions (id, vault_id, tx_hash, protocol_name, action, token_address, amount, gas_used, status, block_number, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
        """, tx_id, vault_id, tx_hash_hex, None, 'send', None, str(tx.amount), '0.0', 'pending', 0)
        
        return {"tx_hash": tx_hash_hex, "status": "pending"}

@api_router.get("/vaults/{vault_id}/transactions")
async def get_transactions(vault_id: str, user_id: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        # Verify vault ownership
        vault = await conn.fetchrow("SELECT id FROM user_vaults WHERE id = $1 AND user_id = $2", vault_id, user_id)
        if not vault:
            raise HTTPException(status_code=404, detail="Vault not found")
        
        txs = await conn.fetch("SELECT id, tx_hash, action, amount, status, timestamp FROM vault_transactions WHERE vault_id = $1 ORDER BY timestamp DESC LIMIT 50", vault_id)
        return [{"id": t['id'], "tx_hash": t['tx_hash'], "action": t['action'], "amount": t['amount'], "status": t['status'], "timestamp": t['timestamp'].isoformat()} for t in txs]

# DeFi Integration endpoints
@api_router.get("/defi/protocols")
async def get_protocols():
    return [
        {"name": "Aave", "address": os.environ['AAVE_POOL'], "type": "lending"},
        {"name": "Compound", "address": os.environ['COMPOUND_COMET'], "type": "lending"}
    ]

@api_router.get("/")
async def root():
    return {"message": "Vault Wallet API", "status": "online"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)