"""
ArtCube Wallet - Aave Direct Connection
Checks and manages Aave interaction for the ArtCube wallet
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from web3 import Web3
import logging

from aave_integration import AaveIntegration, AAVE_ADDRESSES

router = APIRouter(prefix="/artcube", tags=["ArtCube Wallet"])
logger = logging.getLogger(__name__)

# ArtCube wallet address
ARTCUBE_ADDRESS = os.environ.get("ARTCUBE_WALLET_ADDRESS")

# Initialize Web3
ETHEREUM_RPC = os.environ.get("ETHEREUM_RPC_URL")
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC))

# Initialize Aave integration
aave = AaveIntegration(w3)


class AaveConnectionResponse(BaseModel):
    wallet_address: str
    aave_pool_address: str
    connected: bool
    eth_balance: str
    can_interact: bool
    message: str


@router.get("/aave-connection", response_model=AaveConnectionResponse)
async def check_aave_connection():
    """
    Check if ArtCube wallet is properly connected to Aave Pool
    """
    try:
        if not ARTCUBE_ADDRESS:
            raise HTTPException(status_code=500, detail="ArtCube wallet address not configured")
        
        # Check ETH balance
        eth_balance_wei = w3.eth.get_balance(ARTCUBE_ADDRESS)
        eth_balance = w3.from_wei(eth_balance_wei, 'ether')
        
        # Check if wallet has enough ETH for transactions
        has_gas = float(eth_balance) > 0.001  # At least 0.001 ETH for gas
        
        # Verify Aave Pool address is correct
        pool_address = AAVE_ADDRESSES["Pool"]
        
        # Check if Aave Pool contract exists
        pool_code = w3.eth.get_code(pool_address)
        pool_exists = len(pool_code) > 0
        
        can_interact = has_gas and pool_exists
        
        if can_interact:
            message = "✅ ArtCube wallet is ready to interact with Aave!"
        elif not has_gas:
            message = f"⚠️ Need ETH for gas. Current: {float(eth_balance):.6f} ETH"
        elif not pool_exists:
            message = "❌ Aave Pool contract not found at address"
        else:
            message = "❌ Cannot connect to Aave"
        
        return AaveConnectionResponse(
            wallet_address=ARTCUBE_ADDRESS,
            aave_pool_address=pool_address,
            connected=pool_exists,
            eth_balance=f"{float(eth_balance):.6f}",
            can_interact=can_interact,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error checking Aave connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallet-info")
async def get_artcube_wallet_info():
    """Get ArtCube wallet information"""
    try:
        if not ARTCUBE_ADDRESS:
            raise HTTPException(status_code=500, detail="ArtCube wallet address not configured")
        
        # Get ETH balance
        eth_balance_wei = w3.eth.get_balance(ARTCUBE_ADDRESS)
        eth_balance = w3.from_wei(eth_balance_wei, 'ether')
        
        # Get token balances (USDC, USDT, etc.)
        USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
        
        ERC20_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
        usdt_contract = w3.eth.contract(address=USDT_ADDRESS, abi=ERC20_ABI)
        
        usdc_balance = usdc_contract.functions.balanceOf(ARTCUBE_ADDRESS).call()
        usdt_balance = usdt_contract.functions.balanceOf(ARTCUBE_ADDRESS).call()
        
        return {
            "wallet_address": ARTCUBE_ADDRESS,
            "wallet_name": "ArtCube",
            "balances": {
                "ETH": {
                    "balance": float(eth_balance),
                    "formatted": f"{float(eth_balance):.6f} ETH"
                },
                "USDC": {
                    "balance": usdc_balance,
                    "formatted": f"{usdc_balance / 1e6:.2f} USDC"
                },
                "USDT": {
                    "balance": usdt_balance,
                    "formatted": f"{usdt_balance / 1e6:.2f} USDT"
                }
            },
            "aave_pool": AAVE_ADDRESSES["Pool"],
            "ready_for_aave": float(eth_balance) > 0.001
        }
        
    except Exception as e:
        logger.error(f"Error getting wallet info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify-aave-address")
async def verify_aave_address():
    """Verify the Aave Pool address is correct"""
    try:
        pool_address = AAVE_ADDRESSES["Pool"]
        
        # Get contract bytecode
        code = w3.eth.get_code(pool_address)
        
        # Check if contract exists
        contract_exists = len(code) > 0
        
        # Known correct Aave V3 Pool address
        OFFICIAL_AAVE_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
        
        address_match = pool_address.lower() == OFFICIAL_AAVE_POOL.lower()
        
        return {
            "configured_address": pool_address,
            "official_address": OFFICIAL_AAVE_POOL,
            "addresses_match": address_match,
            "contract_exists": contract_exists,
            "contract_bytecode_length": len(code),
            "status": "✅ CORRECT" if (address_match and contract_exists) else "❌ WRONG"
        }
        
    except Exception as e:
        logger.error(f"Error verifying Aave address: {e}")
        raise HTTPException(status_code=500, detail=str(e))
