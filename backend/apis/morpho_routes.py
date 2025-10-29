from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from web3 import Web3
from eth_account import Account
import logging
import sys
sys.path.append('/app/backend')

from libs.morpho_blue import (
    MORPHO_BLUE_ADDRESS,
    MORPHO_BLUE_ABI,
    ACS_TOKEN_ADDRESS,
    ACS_PRICE_FEED_ADDRESS,
    ACS_PRICE_FEED_ABI,
    USDC_ADDRESS,
    DEFAULT_ACS_USDC_MARKET,
    calculate_market_id
)

from apis.morpho_deps import db, w3, decrypt_private_key
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

router = APIRouter(prefix="/morpho", tags=["Morpho Blue"])

# Auth setup
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user_id"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Request/Response Models
class SupplyCollateralRequest(BaseModel):
    vault_id: str
    amount: float  # Amount in ACS tokens

class SupplyCollateralResponse(BaseModel):
    success: bool
    message: str
    transaction_hash: str | None = None

class BorrowRequest(BaseModel):
    vault_id: str
    amount: float  # Amount in USDC

class BorrowResponse(BaseModel):
    success: bool
    message: str
    transaction_hash: str | None = None

class RepayRequest(BaseModel):
    vault_id: str
    amount: float  # Amount in USDC

class RepayResponse(BaseModel):
    success: bool
    message: str
    transaction_hash: str | None = None

class WithdrawCollateralRequest(BaseModel):
    vault_id: str
    amount: float  # Amount in ACS tokens

class WithdrawCollateralResponse(BaseModel):
    success: bool
    message: str
    transaction_hash: str | None = None

class PositionResponse(BaseModel):
    wallet_address: str
    supply_shares: int
    borrow_shares: int
    collateral: int
    collateral_formatted: float
    borrow_formatted: float

class ACSPriceResponse(BaseModel):
    price: float
    decimals: int
    updated_at: int

class MarketInfoResponse(BaseModel):
    market_id: str
    total_supply_assets: float
    total_borrow_assets: float
    utilization_rate: float
    lltv: float

# ERC20 ABI for approvals
ERC20_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]


@router.get("/acs-price", response_model=ACSPriceResponse)
async def get_acs_price():
    """Get current ACS token price from price feed"""
    try:
        price_feed = w3.eth.contract(
            address=Web3.to_checksum_address(ACS_PRICE_FEED_ADDRESS),
            abi=ACS_PRICE_FEED_ABI
        )

        # Get latest price
        latest_data = price_feed.functions.latestRoundData().call()
        decimals = price_feed.functions.decimals().call()

        price = latest_data[1]  # answer
        updated_at = latest_data[3]  # updatedAt

        # Convert to human-readable format
        price_formatted = price / (10 ** decimals)

        return ACSPriceResponse(
            price=price_formatted,
            decimals=decimals,
            updated_at=updated_at
        )

    except Exception as e:
        logging.error(f"Error fetching ACS price: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-info", response_model=MarketInfoResponse)
async def get_market_info():
    """Get Morpho Blue ACS/USDC market information"""
    try:
        market_params = DEFAULT_ACS_USDC_MARKET
        market_id = calculate_market_id(market_params)
        
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        market = morpho_contract.functions.market(market_id).call()
        
        total_supply_assets = market[0] / 1e6  # USDC decimals
        total_borrow_assets = market[2] / 1e6  # USDC decimals
        
        utilization_rate = (total_borrow_assets / total_supply_assets * 100) if total_supply_assets > 0 else 0
        lltv = market_params['lltv'] / 1e18 * 100  # Convert to percentage
        
        return MarketInfoResponse(
            market_id=market_id.hex(),
            total_supply_assets=total_supply_assets,
            total_borrow_assets=total_borrow_assets,
            utilization_rate=utilization_rate,
            lltv=lltv
        )
        
    except Exception as e:
        logging.error(f"Error fetching market info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/supply-collateral", response_model=SupplyCollateralResponse)
async def supply_collateral(request: SupplyCollateralRequest, user_id: str = Depends(get_current_user)):
    """Supply ACS collateral to Morpho Blue"""
    try:
        # Get vault
        vault = await db.user_vaults.find_one({"id": request.vault_id, "user_id": user_id})
        if not vault:
            raise HTTPException(status_code=404, detail="Vault not found")
        
        # Check if vault has private key
        if vault['private_key_encrypted'] == b'watch_only_no_private_key':
            raise HTTPException(status_code=403, detail="Cannot transact from watch-only wallet")
        
        # Decrypt private key
        private_key = decrypt_private_key(vault['private_key_encrypted'])
        account = Account.from_key(private_key)
        
        # Get market params
        market_params = DEFAULT_ACS_USDC_MARKET
        
        # Convert amount to wei (ACS has 18 decimals)
        amount_in_wei = int(request.amount * 1e18)
        
        # Step 1: Approve Morpho Blue to spend ACS tokens
        acs_contract = w3.eth.contract(
            address=Web3.to_checksum_address(ACS_TOKEN_ADDRESS),
            abi=ERC20_ABI
        )
        
        allowance = acs_contract.functions.allowance(
            account.address,
            Web3.to_checksum_address(MORPHO_BLUE_ADDRESS)
        ).call()
        
        if allowance < amount_in_wei:
            approve_tx = acs_contract.functions.approve(
                Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
                amount_in_wei
            ).build_transaction({
                'from': account.address,
                'nonce': w3.eth.get_transaction_count(account.address),
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'chainId': 1
            })
            
            signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key)
            approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            w3.eth.wait_for_transaction_receipt(approve_hash)
            logging.info(f"Approved Morpho Blue to spend ACS: {approve_hash.hex()}")
        
        # Step 2: Supply collateral to Morpho Blue
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        market_params_tuple = (
            Web3.to_checksum_address(market_params['loanToken']),
            Web3.to_checksum_address(market_params['collateralToken']),
            Web3.to_checksum_address(market_params['oracle']),
            Web3.to_checksum_address(market_params['irm']),
            market_params['lltv']
        )
        
        supply_tx = morpho_contract.functions.supplyCollateral(
            market_params_tuple,
            amount_in_wei,
            account.address,
            b''  # empty data
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 1
        })
        
        signed_tx = w3.eth.account.sign_transaction(supply_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        logging.info(f"Morpho Blue supply collateral: {tx_hash.hex()}")
        
        return SupplyCollateralResponse(
            success=True,
            message=f"Successfully supplied {request.amount} ACS as collateral",
            transaction_hash=tx_hash.hex()
        )
        
    except Exception as e:
        logging.error(f"Error supplying collateral: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/borrow", response_model=BorrowResponse)
async def borrow(request: BorrowRequest, user_id: str = Depends(get_current_user)):
    """Borrow USDC from Morpho Blue against ACS collateral"""
    try:
        # Get vault
        vault = await db.user_vaults.find_one({"id": request.vault_id, "user_id": user_id})
        if not vault:
            raise HTTPException(status_code=404, detail="Vault not found")
        
        if vault['private_key_encrypted'] == b'watch_only_no_private_key':
            raise HTTPException(status_code=403, detail="Cannot transact from watch-only wallet")
        
        private_key = decrypt_private_key(vault['private_key_encrypted'])
        account = Account.from_key(private_key)
        
        market_params = DEFAULT_ACS_USDC_MARKET
        
        # USDC has 6 decimals
        amount_in_smallest_unit = int(request.amount * 1e6)
        
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        market_params_tuple = (
            Web3.to_checksum_address(market_params['loanToken']),
            Web3.to_checksum_address(market_params['collateralToken']),
            Web3.to_checksum_address(market_params['oracle']),
            Web3.to_checksum_address(market_params['irm']),
            market_params['lltv']
        )
        
        borrow_tx = morpho_contract.functions.borrow(
            market_params_tuple,
            amount_in_smallest_unit,
            0,  # shares (0 means use assets)
            account.address,  # onBehalf
            account.address   # receiver
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 1
        })
        
        signed_tx = w3.eth.account.sign_transaction(borrow_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        logging.info(f"Morpho Blue borrow: {tx_hash.hex()}")
        
        return BorrowResponse(
            success=True,
            message=f"Successfully borrowed {request.amount} USDC",
            transaction_hash=tx_hash.hex()
        )
        
    except Exception as e:
        logging.error(f"Error borrowing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repay", response_model=RepayResponse)
async def repay(request: RepayRequest, user_id: str = Depends(get_current_user)):
    """Repay USDC debt in Morpho Blue"""
    try:
        # Get vault
        vault = await db.user_vaults.find_one({"id": request.vault_id, "user_id": user_id})
        if not vault:
            raise HTTPException(status_code=404, detail="Vault not found")
        
        if vault['private_key_encrypted'] == b'watch_only_no_private_key':
            raise HTTPException(status_code=403, detail="Cannot transact from watch-only wallet")
        
        private_key = decrypt_private_key(vault['private_key_encrypted'])
        account = Account.from_key(private_key)
        
        market_params = DEFAULT_ACS_USDC_MARKET
        
        # USDC has 6 decimals
        amount_in_smallest_unit = int(request.amount * 1e6)
        
        # Step 1: Approve Morpho Blue to spend USDC tokens
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI
        )
        
        allowance = usdc_contract.functions.allowance(
            account.address,
            Web3.to_checksum_address(MORPHO_BLUE_ADDRESS)
        ).call()
        
        if allowance < amount_in_smallest_unit:
            approve_tx = usdc_contract.functions.approve(
                Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
                amount_in_smallest_unit
            ).build_transaction({
                'from': account.address,
                'nonce': w3.eth.get_transaction_count(account.address),
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'chainId': 1
            })
            
            signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key)
            approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            w3.eth.wait_for_transaction_receipt(approve_hash)
            logging.info(f"Approved Morpho Blue to spend USDC: {approve_hash.hex()}")
        
        # Step 2: Repay debt
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        market_params_tuple = (
            Web3.to_checksum_address(market_params['loanToken']),
            Web3.to_checksum_address(market_params['collateralToken']),
            Web3.to_checksum_address(market_params['oracle']),
            Web3.to_checksum_address(market_params['irm']),
            market_params['lltv']
        )
        
        repay_tx = morpho_contract.functions.repay(
            market_params_tuple,
            amount_in_smallest_unit,
            0,  # shares (0 means use assets)
            account.address,  # onBehalf
            b''  # empty data
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 1
        })
        
        signed_tx = w3.eth.account.sign_transaction(repay_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        logging.info(f"Morpho Blue repay: {tx_hash.hex()}")
        
        return RepayResponse(
            success=True,
            message=f"Successfully repaid {request.amount} USDC",
            transaction_hash=tx_hash.hex()
        )
        
    except Exception as e:
        logging.error(f"Error repaying: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/withdraw-collateral", response_model=WithdrawCollateralResponse)
async def withdraw_collateral(request: WithdrawCollateralRequest, user_id: str = Depends(get_current_user)):
    """Withdraw ACS collateral from Morpho Blue"""
    try:
        # Get vault
        vault = await db.user_vaults.find_one({"id": request.vault_id, "user_id": user_id})
        if not vault:
            raise HTTPException(status_code=404, detail="Vault not found")
        
        if vault['private_key_encrypted'] == b'watch_only_no_private_key':
            raise HTTPException(status_code=403, detail="Cannot transact from watch-only wallet")
        
        private_key = decrypt_private_key(vault['private_key_encrypted'])
        account = Account.from_key(private_key)
        
        market_params = DEFAULT_ACS_USDC_MARKET
        
        # Convert amount to wei (ACS has 18 decimals)
        amount_in_wei = int(request.amount * 1e18)
        
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        market_params_tuple = (
            Web3.to_checksum_address(market_params['loanToken']),
            Web3.to_checksum_address(market_params['collateralToken']),
            Web3.to_checksum_address(market_params['oracle']),
            Web3.to_checksum_address(market_params['irm']),
            market_params['lltv']
        )
        
        withdraw_tx = morpho_contract.functions.withdrawCollateral(
            market_params_tuple,
            amount_in_wei,
            account.address,  # onBehalf
            account.address   # receiver
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 1
        })
        
        signed_tx = w3.eth.account.sign_transaction(withdraw_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        logging.info(f"Morpho Blue withdraw collateral: {tx_hash.hex()}")
        
        return WithdrawCollateralResponse(
            success=True,
            message=f"Successfully withdrew {request.amount} ACS collateral",
            transaction_hash=tx_hash.hex()
        )
        
    except Exception as e:
        logging.error(f"Error withdrawing collateral: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position/{vault_id}", response_model=PositionResponse)
async def get_position(vault_id: str, user_id: str = Depends(get_current_user)):
    """Get user position in Morpho Blue ACS/USDC market"""
    try:
        # Get vault
        vault = await db.user_vaults.find_one({"id": vault_id, "user_id": user_id})
        if not vault:
            raise HTTPException(status_code=404, detail="Vault not found")
        
        wallet_address = vault['vault_address']
        
        market_params = DEFAULT_ACS_USDC_MARKET
        market_id = calculate_market_id(market_params)
        
        morpho_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
            abi=MORPHO_BLUE_ABI
        )
        
        position = morpho_contract.functions.position(
            market_id,
            Web3.to_checksum_address(wallet_address)
        ).call()
        
        supply_shares = position[0]
        borrow_shares = position[1]
        collateral = position[2]
        
        # Format values
        collateral_formatted = collateral / 1e18  # ACS has 18 decimals
        borrow_formatted = borrow_shares / 1e6  # USDC has 6 decimals
        
        return PositionResponse(
            wallet_address=wallet_address,
            supply_shares=supply_shares,
            borrow_shares=borrow_shares,
            collateral=collateral,
            collateral_formatted=collateral_formatted,
            borrow_formatted=borrow_formatted
        )
        
    except Exception as e:
        logging.error(f"Error fetching position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
