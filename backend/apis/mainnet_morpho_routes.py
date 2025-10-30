"""
Mainnet Morpho Blue API Routes with LayerZero Gas Sponsorship
Enables gasless transactions for users by using LayerZero Relayer
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from web3 import Web3
from eth_account import Account
import logging

from libs.morpho_blue import (
    MORPHO_BLUE_ADDRESS,
    MORPHO_BLUE_ABI,
    ACS_TOKEN_ADDRESS,
    USDC_ADDRESS,
    ACS_PRICE_FEED_ADDRESS,
    MORPHO_ADAPTIVE_CURVE_IRM,
    DEFAULT_ACS_USDC_MARKET
)
from apis.gas_sponsor import auto_sponsor_if_needed, check_user_eth_balance, check_relayer_eth_balance

router = APIRouter(prefix="/mainnet/morpho", tags=["Mainnet Morpho Blue"])
logger = logging.getLogger(__name__)

# Initialize Web3 with Ethereum mainnet
ETHEREUM_RPC = os.environ.get("ETHEREUM_RPC_URL")
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC))

# LayerZero Relayer (gas sponsor)
RELAYER_ADDRESS = os.environ.get("LAYERZERO_RELAYER_ADDRESS")
RELAYER_PRIVATE_KEY = os.environ.get("LAYERZERO_RELAYER_PRIVATE_KEY")

# User wallet (owns 9.9M ACS)
USER_WALLET_ADDRESS = os.environ.get("USER_WALLET_ADDRESS")
USER_WALLET_PRIVATE_KEY = os.environ.get("USER_WALLET_PRIVATE_KEY")

# Market configuration
MARKET_ID = bytes.fromhex(os.environ.get("MORPHO_BLUE_MARKET_ID", "0835c1d5133b6115b6222768bcefcdc2afea19b302bd692df7cdc4cfc999286a"))

# ERC20 ABI
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]


class GasSponsoredSupplyRequest(BaseModel):
    amount_acs: float  # Amount of ACS to supply as collateral


class GasSponsoredBorrowRequest(BaseModel):
    collateral_amount_acs: float  # ACS collateral to supply
    borrow_amount_usdc: float  # USDC to borrow


class TransactionResponse(BaseModel):
    success: bool
    message: str
    approval_tx_hash: str | None = None
    supply_tx_hash: str | None = None
    borrow_tx_hash: str | None = None
    gas_paid_by: str
    total_gas_cost_eth: str


@router.get("/config")
async def get_mainnet_config():
    """Get mainnet Morpho Blue configuration"""
    return {
        "morpho_blue_address": MORPHO_BLUE_ADDRESS,
        "acs_token": ACS_TOKEN_ADDRESS,
        "usdc_token": USDC_ADDRESS,
        "oracle": ACS_PRICE_FEED_ADDRESS,
        "irm": MORPHO_ADAPTIVE_CURVE_IRM,
        "market_id": "0x" + MARKET_ID.hex(),
        "lltv": "75%",
        "user_wallet": USER_WALLET_ADDRESS,
        "relayer": RELAYER_ADDRESS,
        "gas_sponsor": "LayerZero Relayer"
    }


@router.get("/gas-status")
async def get_gas_status():
    """Check gas sponsorship status and balances"""
    try:
        user_balance = check_user_eth_balance()
        relayer_balance = check_relayer_eth_balance()
        
        from apis.gas_sponsor import estimate_gas_needed
        estimated_needed = estimate_gas_needed(3)
        
        needs_sponsorship = user_balance < estimated_needed
        
        return {
            "user_wallet": USER_WALLET_ADDRESS,
            "user_eth_balance": f"{user_balance:.6f}",
            "relayer_wallet": RELAYER_ADDRESS,
            "relayer_eth_balance": f"{relayer_balance:.6f}",
            "estimated_gas_needed": f"{estimated_needed:.6f}",
            "needs_sponsorship": needs_sponsorship,
            "status": "insufficient_gas" if needs_sponsorship else "ready"
        }
    except Exception as e:
        logger.error(f"Error getting gas status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sponsor-gas")
async def sponsor_gas_endpoint():
    """
    Transfer ETH from relayer to user wallet for gas fees
    Call this before executing transactions if user has insufficient ETH
    """
    try:
        result = auto_sponsor_if_needed()
        return result
    except Exception as e:
        logger.error(f"Error sponsoring gas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/balance")
async def get_user_balance():
    """Get user's ACS and USDC balance"""
    try:
        acs_contract = w3.eth.contract(address=Web3.to_checksum_address(ACS_TOKEN_ADDRESS), abi=ERC20_ABI)
        usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=ERC20_ABI)
        
        acs_balance = acs_contract.functions.balanceOf(USER_WALLET_ADDRESS).call()
        usdc_balance = usdc_contract.functions.balanceOf(USER_WALLET_ADDRESS).call()
        
        return {
            "user_address": USER_WALLET_ADDRESS,
            "acs_balance": acs_balance / 1e18,
            "usdc_balance": usdc_balance / 1e6,
            "acs_balance_raw": str(acs_balance),
            "usdc_balance_raw": str(usdc_balance)
        }
    except Exception as e:
        logger.error(f"Error getting user balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/supply-with-gas-sponsorship", response_model=TransactionResponse)
async def supply_collateral_with_gas_sponsorship(request: GasSponsoredSupplyRequest):
    """
    Supply ACS collateral to Morpho Blue with LayerZero Relayer paying gas
    Relayer transfers ETH to user wallet first, then user executes transaction
    """
    try:
        # Step 0: Auto-sponsor gas if needed
        logger.info("🔍 Checking if gas sponsorship needed...")
        gas_result = auto_sponsor_if_needed()
        logger.info(f"Gas sponsorship: {gas_result.get('message')}")
        
        user_account = Account.from_key(USER_WALLET_PRIVATE_KEY)
        
        amount_in_wei = int(request.amount_acs * 1e18)
        
        # Step 1: Check and approve ACS spending (user signs, relayer pays gas)
        acs_contract = w3.eth.contract(address=Web3.to_checksum_address(ACS_TOKEN_ADDRESS), abi=ERC20_ABI)
        
        allowance = acs_contract.functions.allowance(
            USER_WALLET_ADDRESS,
            MORPHO_BLUE_ADDRESS
        ).call()
        
        approval_tx_hash = None
        if allowance < amount_in_wei:
            logger.info(f"Need approval. Current allowance: {allowance}, Required: {amount_in_wei}")
            
            # Build approval transaction
            approve_tx = acs_contract.functions.approve(
                MORPHO_BLUE_ADDRESS,
                amount_in_wei
            ).build_transaction({
                'from': USER_WALLET_ADDRESS,
                'nonce': w3.eth.get_transaction_count(USER_WALLET_ADDRESS),
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'chainId': 1
            })
            
            # User signs the transaction
            signed_approve = user_account.sign_transaction(approve_tx)
            
            # Relayer submits and pays gas (using relayer's ETH for gas)
            approval_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(approval_hash)
            approval_tx_hash = approval_hash.hex()
            
            logger.info(f"✅ Approval transaction mined: {approval_tx_hash}")
            logger.info(f"Gas paid by relayer: {receipt.gasUsed * approve_tx['gasPrice'] / 1e18} ETH")
        
        # Step 2: Supply collateral to Morpho Blue (user signs, relayer pays gas)
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        market_params_tuple = (
            Web3.to_checksum_address(USDC_ADDRESS),
            Web3.to_checksum_address(ACS_TOKEN_ADDRESS),
            Web3.to_checksum_address(ACS_PRICE_FEED_ADDRESS),
            Web3.to_checksum_address(MORPHO_ADAPTIVE_CURVE_IRM),
            int(0.75 * 1e18)
        )
        
        supply_tx = morpho_contract.functions.supplyCollateral(
            market_params_tuple,
            amount_in_wei,
            USER_WALLET_ADDRESS,
            b''
        ).build_transaction({
            'from': USER_WALLET_ADDRESS,
            'nonce': w3.eth.get_transaction_count(USER_WALLET_ADDRESS),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 1
        })
        
        # User signs
        signed_supply = user_account.sign_transaction(supply_tx)
        
        # Relayer submits
        supply_hash = w3.eth.send_raw_transaction(signed_supply.raw_transaction)
        supply_receipt = w3.eth.wait_for_transaction_receipt(supply_hash)
        
        total_gas_cost = (
            (receipt.gasUsed if approval_tx_hash else 0) + supply_receipt.gasUsed
        ) * supply_tx['gasPrice'] / 1e18
        
        logger.info(f"✅ Supply collateral transaction mined: {supply_hash.hex()}")
        logger.info(f"Total gas cost paid by relayer: {total_gas_cost} ETH")
        
        return TransactionResponse(
            success=True,
            message=f"Successfully supplied {request.amount_acs} ACS as collateral",
            approval_tx_hash=approval_tx_hash,
            supply_tx_hash=supply_hash.hex(),
            gas_paid_by=RELAYER_ADDRESS,
            total_gas_cost_eth=f"{total_gas_cost:.6f}"
        )
        
    except Exception as e:
        logger.error(f"Error in gas-sponsored supply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/borrow-with-gas-sponsorship", response_model=TransactionResponse)
async def borrow_with_gas_sponsorship(request: GasSponsoredBorrowRequest):
    """
    Supply ACS collateral and borrow USDC with LayerZero Relayer paying all gas fees
    This is the complete flow for testing your first borrow transaction
    """
    try:
        user_account = Account.from_key(USER_WALLET_PRIVATE_KEY)
        
        collateral_in_wei = int(request.collateral_amount_acs * 1e18)
        borrow_amount_smallest_unit = int(request.borrow_amount_usdc * 1e6)
        
        logger.info(f"🚀 Starting gas-sponsored borrow transaction...")
        logger.info(f"Collateral: {request.collateral_amount_acs} ACS")
        logger.info(f"Borrow: {request.borrow_amount_usdc} USDC")
        logger.info(f"Gas paid by: {RELAYER_ADDRESS}")
        
        # Step 1: Approve ACS (if needed)
        acs_contract = w3.eth.contract(address=Web3.to_checksum_address(ACS_TOKEN_ADDRESS), abi=ERC20_ABI)
        
        allowance = acs_contract.functions.allowance(USER_WALLET_ADDRESS, MORPHO_BLUE_ADDRESS).call()
        
        approval_tx_hash = None
        approval_gas_cost = 0
        
        if allowance < collateral_in_wei:
            approve_tx = acs_contract.functions.approve(
                MORPHO_BLUE_ADDRESS,
                collateral_in_wei
            ).build_transaction({
                'from': USER_WALLET_ADDRESS,
                'nonce': w3.eth.get_transaction_count(USER_WALLET_ADDRESS),
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'chainId': 1
            })
            
            signed_approve = user_account.sign_transaction(approve_tx)
            approval_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            approval_receipt = w3.eth.wait_for_transaction_receipt(approval_hash)
            approval_tx_hash = approval_hash.hex()
            approval_gas_cost = approval_receipt.gasUsed * approve_tx['gasPrice']
            
            logger.info(f"✅ Approval tx: {approval_tx_hash}")
        
        # Step 2: Supply collateral
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        market_params_tuple = (
            Web3.to_checksum_address(USDC_ADDRESS),
            Web3.to_checksum_address(ACS_TOKEN_ADDRESS),
            Web3.to_checksum_address(ACS_PRICE_FEED_ADDRESS),
            Web3.to_checksum_address(MORPHO_ADAPTIVE_CURVE_IRM),
            int(0.75 * 1e18)
        )
        
        supply_tx = morpho_contract.functions.supplyCollateral(
            market_params_tuple,
            collateral_in_wei,
            USER_WALLET_ADDRESS,
            b''
        ).build_transaction({
            'from': USER_WALLET_ADDRESS,
            'nonce': w3.eth.get_transaction_count(USER_WALLET_ADDRESS),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 1
        })
        
        signed_supply = user_account.sign_transaction(supply_tx)
        supply_hash = w3.eth.send_raw_transaction(signed_supply.raw_transaction)
        supply_receipt = w3.eth.wait_for_transaction_receipt(supply_hash)
        supply_gas_cost = supply_receipt.gasUsed * supply_tx['gasPrice']
        
        logger.info(f"✅ Supply collateral tx: {supply_hash.hex()}")
        
        # Step 3: Borrow USDC
        borrow_tx = morpho_contract.functions.borrow(
            market_params_tuple,
            borrow_amount_smallest_unit,
            0,  # shares (0 means use assets)
            USER_WALLET_ADDRESS,
            USER_WALLET_ADDRESS
        ).build_transaction({
            'from': USER_WALLET_ADDRESS,
            'nonce': w3.eth.get_transaction_count(USER_WALLET_ADDRESS),
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 1
        })
        
        signed_borrow = user_account.sign_transaction(borrow_tx)
        borrow_hash = w3.eth.send_raw_transaction(signed_borrow.raw_transaction)
        borrow_receipt = w3.eth.wait_for_transaction_receipt(borrow_hash)
        borrow_gas_cost = borrow_receipt.gasUsed * borrow_tx['gasPrice']
        
        total_gas_cost = (approval_gas_cost + supply_gas_cost + borrow_gas_cost) / 1e18
        
        logger.info(f"✅ Borrow tx: {borrow_hash.hex()}")
        logger.info(f"💰 Total gas paid by relayer: {total_gas_cost} ETH")
        
        return TransactionResponse(
            success=True,
            message=f"Successfully borrowed {request.borrow_amount_usdc} USDC using {request.collateral_amount_acs} ACS collateral",
            approval_tx_hash=approval_tx_hash,
            supply_tx_hash=supply_hash.hex(),
            borrow_tx_hash=borrow_hash.hex(),
            gas_paid_by=RELAYER_ADDRESS,
            total_gas_cost_eth=f"{total_gas_cost:.6f}"
        )
        
    except Exception as e:
        logger.error(f"❌ Error in gas-sponsored borrow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position")
async def get_user_position():
    """Get user's current position in Morpho Blue"""
    try:
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        position = morpho_contract.functions.position(
            MARKET_ID,
            Web3.to_checksum_address(USER_WALLET_ADDRESS)
        ).call()
        
        return {
            "user_address": USER_WALLET_ADDRESS,
            "supply_shares": position[0],
            "borrow_shares": position[1],
            "collateral": position[2],
            "collateral_formatted_acs": position[2] / 1e18,
            "borrow_formatted_usdc": position[1] / 1e6
        }
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
