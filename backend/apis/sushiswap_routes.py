"""
SushiSwap V3 API Routes
Provides endpoints for SushiSwap pool interaction
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from web3 import Web3
import logging

from sushiswap_integration import SushiSwapIntegration, SUSHISWAP_V3_POOL

router = APIRouter(prefix="/sushiswap", tags=["SushiSwap"])
logger = logging.getLogger(__name__)

# Initialize Web3
ETHEREUM_RPC = os.environ.get("ETHEREUM_RPC_URL")
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC))

# Initialize SushiSwap integration
sushi = SushiSwapIntegration(w3)


class PoolInfoResponse(BaseModel):
    pool_address: str
    pool_url: str
    token0: dict
    token1: dict
    fee_tier: float
    liquidity: str
    current_price: float
    current_tick: int
    pair_name: str


class UserPositionResponse(BaseModel):
    wallet_address: str
    pool_address: str
    token0_balance: float
    token1_balance: float
    token0_symbol: str
    token1_symbol: str


@router.get("/pool-info", response_model=PoolInfoResponse)
async def get_pool_info():
    """Get information about the SushiSwap V3 pool"""
    try:
        info = sushi.get_pool_info()
        return PoolInfoResponse(**info)
    except Exception as e:
        logger.error(f"Error getting pool info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position/{wallet_address}", response_model=UserPositionResponse)
async def get_user_position(wallet_address: str):
    """Get user's position in the SushiSwap pool"""
    try:
        position = sushi.get_user_position(wallet_address)
        return UserPositionResponse(**position)
    except Exception as e:
        logger.error(f"Error getting user position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pool-link")
async def get_pool_link():
    """Get direct link to SushiSwap pool"""
    return {
        "pool_address": SUSHISWAP_V3_POOL,
        "pool_url": f"https://www.sushi.com/ethereum/pool/v3/{SUSHISWAP_V3_POOL}",
        "description": "SushiSwap V3 Pool - Click to view on SushiSwap"
    }
