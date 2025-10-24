from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt
from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
import base64
from euler_integration import EulerV2Integration, EULER_ADDRESSES
from multi_token import MultiTokenManager
from token_config import TOKEN_CONFIG
from aave_integration import AaveIntegration
from compound_integration import CompoundIntegration

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'vault_wallet')]

# Web3 setup
ALCHEMY_URL = f"https://eth-mainnet.g.alchemy.com/v2/{os.environ['ALCHEMY_API_KEY']}"
w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))

# Initialize Euler V2 Integration
euler = EulerV2Integration(w3)

# Initialize Multi-Token Manager
token_manager = MultiTokenManager(w3)

# Initialize Aave Integration
aave = AaveIntegration(w3)

# Initialize Compound Integration
compound = CompoundIntegration(w3)

# Encryption setup
cipher_suite = Fernet(base64.urlsafe_b64encode(bytes.fromhex(os.environ['ENCRYPTION_KEY'])))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

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
    owner_addresses: List[str] = []
    private_key: Optional[str] = None  # For importing existing wallet

class SendTransaction(BaseModel):
    vault_id: str
    to_address: str
    amount: float
    token: str = "ETH"

class DeFiTransaction(BaseModel):
    vault_id: str
    protocol: str  # "aave" or "compound"
    action: str  # "lend" or "borrow"
    token: str
    amount: float

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
    """Get ETH price - using fallback for now"""
    try:
        import requests
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data['ethereum']['usd'])
    except Exception as e:
        logging.warning(f"Error fetching ETH price from API: {e}")
    return 3500.0

async def get_acs_price() -> float:
    """Get ACS token price from custom price feed contract"""
    try:
        price_feed_abi = [
            {
                "inputs": [],
                "name": "getCurrentPrice",
                "outputs": [{"internalType": "int256", "name": "", "type": "int256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        contract = w3.eth.contract(address=os.environ['ACS_PRICE_FEED'], abi=price_feed_abi)
        price = contract.functions.getCurrentPrice().call()
        return float(price) / 10**8
    except Exception as e:
        logging.warning(f"Error fetching ACS price from contract: {e}")
        return 0.78

async def get_acs_balance(vault_address: str) -> float:
    """Get ACS token balance for a vault"""
    try:
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        contract = w3.eth.contract(address=os.environ['ACS_TOKEN'], abi=erc20_abi)
        balance_wei = contract.functions.balanceOf(vault_address).call()
        return float(w3.from_wei(balance_wei, 'ether'))
    except Exception as e:
        logging.warning(f"Error fetching ACS balance for {vault_address}: {e}")
        return 0.0

# Auth endpoints
@api_router.post("/auth/register", response_model=Token)
async def register(user: UserRegister):
    # Check if user exists
    existing = await db.users.find_one({"$or": [{"email": user.email}, {"username": user.username}]})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_pwd = hash_password(user.password)
    await db.users.insert_one({
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "password_hash": hashed_pwd,
        "created_at": datetime.now(timezone.utc)
    })
    
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
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id = user['id']
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
    # Check if user wants to import existing address or create new one
    if vault.owner_addresses and len(vault.owner_addresses) > 0 and vault.owner_addresses[0]:
        # Import existing address (watch-only mode)
        vault_address = vault.owner_addresses[0]
        # Validate address format
        if not w3.is_address(vault_address):
            raise HTTPException(status_code=400, detail="Invalid Ethereum address")
        # Use empty encrypted key for watch-only wallets
        encrypted_key = b'watch_only_no_private_key'
    else:
        # Create new Ethereum account for the vault
        account = Account.create()
        vault_address = account.address
        encrypted_key = encrypt_private_key(account.key.hex())
    
    vault_id = str(uuid.uuid4())
    await db.user_vaults.insert_one({
        "id": vault_id,
        "user_id": user_id,
        "vault_address": vault_address,
        "owner_addresses": [vault_address] if vault.owner_addresses and vault.owner_addresses[0] else vault.owner_addresses,
        "network": "ethereum",
        "vault_type": vault.vault_type,
        "label": vault.label,
        "private_key_encrypted": encrypted_key,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })
    
    return {
        "vault_id": vault_id,
        "vault_address": vault_address,
        "label": vault.label,
        "owner_addresses": [vault_address]
    }

@api_router.get("/vaults")
async def get_vaults(user_id: str = Depends(get_current_user)):
    vaults = await db.user_vaults.find({"user_id": user_id}, {"_id": 0, "private_key_encrypted": 0}).sort("created_at", -1).to_list(100)
    for v in vaults:
        if isinstance(v.get('created_at'), datetime):
            v['created_at'] = v['created_at'].isoformat()
    return vaults

@api_router.get("/vaults/{vault_id}/balance")
async def get_vault_balance(vault_id: str, user_id: str = Depends(get_current_user)):
    vault = await db.user_vaults.find_one({"id": vault_id, "user_id": user_id})
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    
    vault_address = vault['vault_address']
    
    # Get all token balances
    balances = token_manager.get_all_balances(vault_address)
    
    # Get all token prices
    prices = {symbol: token_manager.get_token_price(symbol) for symbol in TOKEN_CONFIG.keys()}
    
    # Calculate USD values
    usd_values = {symbol: balances[symbol] * prices[symbol] for symbol in TOKEN_CONFIG.keys()}
    total_usd = sum(usd_values.values())
    
    return {
        "vault_address": vault_address,
        "balances": balances,
        "prices": prices,
        "usd_values": usd_values,
        "total_usd": total_usd,
        # Legacy fields for compatibility
        "eth_balance": balances.get("ETH", 0.0),
        "eth_usd": usd_values.get("ETH", 0.0),
        "acs_balance": balances.get("ACS", 0.0),
        "acs_usd": usd_values.get("ACS", 0.0)
    }

@api_router.post("/vaults/{vault_id}/send")
async def send_transaction(vault_id: str, tx: SendTransaction, user_id: str = Depends(get_current_user)):
    vault = await db.user_vaults.find_one({"id": vault_id, "user_id": user_id})
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    
    # Check if wallet is watch-only
    if vault['private_key_encrypted'] == b'watch_only_no_private_key':
        raise HTTPException(status_code=403, detail="Cannot send from watch-only wallet. This wallet was imported without a private key.")
    
    # Validate token
    if tx.token not in TOKEN_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unsupported token: {tx.token}")
    
    # Decrypt private key
    try:
        private_key = decrypt_private_key(vault['private_key_encrypted'])
        account = Account.from_key(private_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error decrypting private key: {str(e)}")
    
    # Build transaction using multi-token manager
    try:
        transaction = token_manager.build_transfer_transaction(
            token_symbol=tx.token,
            from_address=vault['vault_address'],
            to_address=tx.to_address,
            amount=tx.amount
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error building transaction: {str(e)}")
    
    # Sign and send
    try:
        signed = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = tx_hash.hex()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending transaction: {str(e)}")
    
    # Store transaction
    tx_id = str(uuid.uuid4())
    token_address = TOKEN_CONFIG[tx.token].get("address")
    await db.vault_transactions.insert_one({
        "id": tx_id,
        "vault_id": vault_id,
        "tx_hash": tx_hash_hex,
        "protocol_name": None,
        "action": "send",
        "token_symbol": tx.token,
        "token_address": token_address,
        "amount": str(tx.amount),
        "gas_used": "0.0",
        "status": "pending",
        "block_number": 0,
        "timestamp": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"tx_hash": tx_hash_hex, "status": "pending", "token": tx.token}

@api_router.get("/vaults/{vault_id}/transactions")
async def get_transactions(vault_id: str, user_id: str = Depends(get_current_user)):
    # Verify vault ownership
    vault = await db.user_vaults.find_one({"id": vault_id, "user_id": user_id})
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    
    txs = await db.vault_transactions.find({"vault_id": vault_id}, {"_id": 0}).sort("timestamp", -1).limit(50).to_list(50)
    for t in txs:
        if isinstance(t.get('timestamp'), datetime):
            t['timestamp'] = t['timestamp'].isoformat()
    return txs

# DeFi Integration endpoints
@api_router.get("/defi/protocols")
async def get_protocols():
    return [
        {"name": "Aave", "address": os.environ['AAVE_POOL'], "type": "lending"},
        {"name": "Compound", "address": os.environ['COMPOUND_COMET'], "type": "lending"},
        {"name": "Euler V2", "address": EULER_ADDRESSES["EVC"], "type": "governed_vaults"}
    ]

@api_router.post("/defi/transaction")
async def execute_defi_transaction(defi_tx: DeFiTransaction, user_id: str = Depends(get_current_user)):
    """Execute Aave or Compound lending/borrowing transaction"""
    vault = await db.user_vaults.find_one({"id": defi_tx.vault_id, "user_id": user_id})
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    
    # Check if wallet is watch-only
    if vault['private_key_encrypted'] == b'watch_only_no_private_key':
        raise HTTPException(status_code=403, detail="Cannot transact from watch-only wallet")
    
    # Get token info
    if defi_tx.token not in TOKEN_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unsupported token: {defi_tx.token}")
    
    token_info = TOKEN_CONFIG[defi_tx.token]
    asset_address = token_info.get("address")
    
    # For native ETH, we need to handle differently
    if defi_tx.token == "ETH":
        # Use WETH for DeFi protocols
        asset_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    
    if not asset_address:
        raise HTTPException(status_code=400, detail="Token address not found")
    
    # Decrypt private key
    try:
        private_key = decrypt_private_key(vault['private_key_encrypted'])
        account = Account.from_key(private_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error decrypting private key: {str(e)}")
    
    # Build transaction based on protocol and action
    try:
        if defi_tx.protocol.lower() == "aave":
            if defi_tx.action.lower() == "lend":
                transaction = aave.build_supply_transaction(
                    asset_address,
                    defi_tx.amount,
                    token_info["decimals"],
                    vault['vault_address']
                )
            elif defi_tx.action.lower() == "borrow":
                transaction = aave.build_borrow_transaction(
                    asset_address,
                    defi_tx.amount,
                    token_info["decimals"],
                    vault['vault_address']
                )
            else:
                raise HTTPException(status_code=400, detail="Invalid action. Use 'lend' or 'borrow'")
        
        elif defi_tx.protocol.lower() == "compound":
            if defi_tx.action.lower() == "lend":
                transaction = compound.build_supply_transaction(
                    asset_address,
                    defi_tx.amount,
                    token_info["decimals"],
                    vault['vault_address']
                )
            else:
                raise HTTPException(status_code=400, detail="Compound borrow not implemented yet")
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error building transaction: {str(e)}")
    
    # Sign and send transaction
    try:
        signed = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = tx_hash.hex()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending transaction: {str(e)}")
    
    # Store transaction
    tx_id = str(uuid.uuid4())
    await db.vault_transactions.insert_one({
        "id": tx_id,
        "vault_id": defi_tx.vault_id,
        "tx_hash": tx_hash_hex,
        "protocol_name": defi_tx.protocol,
        "action": defi_tx.action,
        "token_symbol": defi_tx.token,
        "token_address": asset_address,
        "amount": str(defi_tx.amount),
        "gas_used": "0.0",
        "status": "pending",
        "block_number": 0,
        "timestamp": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc)
    })
    
    return {
        "tx_hash": tx_hash_hex,
        "status": "pending",
        "protocol": defi_tx.protocol,
        "action": defi_tx.action,
        "token": defi_tx.token,
        "amount": defi_tx.amount
    }

# Euler V2 endpoints
@api_router.get("/euler/vaults/{vault_address}/info")
async def get_euler_vault_info(vault_address: str, account: str):
    """Get Euler vault information for an account"""
    try:
        info = euler.get_vault_info(vault_address, account)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/euler/accounts/{account_address}/collaterals")
async def get_euler_collaterals(account_address: str):
    """Get list of collateral vaults for an account"""
    try:
        collaterals = euler.get_account_collaterals(account_address)
        return {"account": account_address, "collaterals": collaterals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/euler/vaults/{vault_address}/health")
async def get_euler_vault_health(vault_address: str, account: str):
    """Get health factor for account in Euler vault"""
    try:
        liquidity = euler.get_account_liquidity(vault_address, account)
        return {
            "vault_address": vault_address,
            "account": account,
            **liquidity
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/euler/contracts")
async def get_euler_contracts():
    """Get Euler V2 contract addresses"""
    return {
        "contracts": EULER_ADDRESSES,
        "network": "ethereum_mainnet",
        "chain_id": 1
    }

@api_router.get("/tokens/acs")
async def get_acs_token():
    """Get ACS token information"""
    token = await db.custom_tokens.find_one({"token_symbol": "ACS"}, {"_id": 0})
    if token:
        return {
            "symbol": token['token_symbol'],
            "name": token['token_name'],
            "address": token['token_address'],
            "decimals": token['decimals'],
            "network": token['network']
        }
    return {"symbol": "ACS", "name": "ACS Token", "address": "N/A", "decimals": 18, "network": "ethereum"}

@api_router.get("/tokens/supported")
async def get_supported_tokens():
    """Get list of all supported tokens"""
    return {
        "tokens": TOKEN_CONFIG,
        "count": len(TOKEN_CONFIG)
    }

@api_router.get("/")
async def root():
    return {"message": "Vault Wallet API", "status": "online", "database": "MongoDB"}

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
