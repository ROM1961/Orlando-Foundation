"""
LayerZero Relayer API Routes
Provides endpoints for relayer monitoring and management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from layerzero_relayer import relayer

router = APIRouter(prefix="/layerzero", tags=["LayerZero Relayer"])
logger = logging.getLogger(__name__)


class RelayerInfoResponse(BaseModel):
    address: str
    supported_chains: List[str]
    status: str
    created_at: str


class ChainBalanceResponse(BaseModel):
    chain: str
    chain_name: Optional[str] = None
    native_token: str
    balance: int
    balance_formatted: str
    address: str
    explorer_url: Optional[str] = None
    error: Optional[str] = None


class RelayerStatusResponse(BaseModel):
    address: str
    status: str
    health: str
    total_native_balance: str
    last_checked: str
    balances: List[dict]
    supported_chains: List[dict]


class TransactionResponse(BaseModel):
    hash: str
    from_address: str = None
    to: str
    value: str
    timestamp: str
    status: str
    chain: str


@router.get("/relayer/info", response_model=RelayerInfoResponse)
async def get_relayer_info():
    """Get basic relayer information"""
    try:
        info = relayer.get_relayer_info()
        return RelayerInfoResponse(**info)
    except Exception as e:
        logger.error(f"Error getting relayer info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relayer/status", response_model=RelayerStatusResponse)
async def get_relayer_status():
    """Get comprehensive relayer status including balances across all chains"""
    try:
        status = relayer.get_relayer_status()
        return RelayerStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting relayer status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relayer/balance/{chain}", response_model=ChainBalanceResponse)
async def get_balance_on_chain(chain: str, user_id: str = Depends(get_current_user_dep())):
    """Get relayer balance on a specific chain"""
    try:
        balance_info = relayer.get_balance_on_chain(chain)
        if "error" in balance_info and balance_info["error"] == f"Unsupported chain: {chain}":
            raise HTTPException(status_code=400, detail=f"Unsupported chain: {chain}")
        return ChainBalanceResponse(**balance_info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting balance on {chain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relayer/balances")
async def get_all_balances(user_id: str = Depends(get_current_user_dep())):
    """Get relayer balances across all supported chains"""
    try:
        balances = relayer.get_all_balances()
        return {
            "relayer_address": relayer.relayer_address,
            "balances": balances
        }
    except Exception as e:
        logger.error(f"Error getting all balances: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relayer/transactions/{chain}")
async def get_recent_transactions(
    chain: str,
    limit: int = 10,
    user_id: str = Depends(get_current_user_dep())
):
    """Get recent relayer transactions on a specific chain"""
    try:
        transactions = relayer.get_recent_transactions(chain, limit)
        return {
            "chain": chain,
            "relayer_address": relayer.relayer_address,
            "transactions": transactions
        }
    except Exception as e:
        logger.error(f"Error getting transactions on {chain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chains")
async def get_supported_chains(user_id: str = Depends(get_current_user_dep())):
    """Get list of all supported chains"""
    try:
        from layerzero_relayer import CHAIN_CONFIG
        
        chains = []
        for chain_key, config in CHAIN_CONFIG.items():
            chains.append({
                "key": chain_key,
                "name": config["name"],
                "chain_id": config.get("chain_id"),
                "native_token": config["native_token"],
                "explorer": config["explorer"]
            })
        
        return {
            "chains": chains,
            "total_chains": len(chains)
        }
    except Exception as e:
        logger.error(f"Error getting supported chains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chain/{chain}/info")
async def get_chain_info(chain: str, user_id: str = Depends(get_current_user_dep())):
    """Get detailed information about a specific chain"""
    try:
        chain_info = relayer.get_chain_info(chain)
        if chain_info is None:
            raise HTTPException(status_code=404, detail=f"Chain not found: {chain}")
        return chain_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chain info for {chain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
