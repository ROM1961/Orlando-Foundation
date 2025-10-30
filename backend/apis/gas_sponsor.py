"""
Gas Sponsorship Module
Transfers ETH from relayer to user wallet to pay for gas fees
"""

import os
from web3 import Web3
from eth_account import Account
import logging

logger = logging.getLogger(__name__)

# Initialize Web3
ETHEREUM_RPC = os.environ.get("ETHEREUM_RPC_URL")
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC))

# Relayer (has ETH for gas)
RELAYER_ADDRESS = os.environ.get("LAYERZERO_RELAYER_ADDRESS")
RELAYER_PRIVATE_KEY = os.environ.get("LAYERZERO_RELAYER_PRIVATE_KEY")

# User wallet
USER_WALLET_ADDRESS = os.environ.get("USER_WALLET_ADDRESS")


def check_user_eth_balance() -> float:
    """Check user's ETH balance"""
    try:
        balance_wei = w3.eth.get_balance(USER_WALLET_ADDRESS)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        return float(balance_eth)
    except Exception as e:
        logger.error(f"Error checking user ETH balance: {e}")
        return 0.0


def check_relayer_eth_balance() -> float:
    """Check relayer's ETH balance"""
    try:
        balance_wei = w3.eth.get_balance(RELAYER_ADDRESS)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        return float(balance_eth)
    except Exception as e:
        logger.error(f"Error checking relayer ETH balance: {e}")
        return 0.0


def estimate_gas_needed(num_transactions: int = 3) -> float:
    """
    Estimate ETH needed for gas
    Average transaction: ~200k gas units
    At 30 gwei: 0.006 ETH per transaction
    """
    gas_price = w3.eth.gas_price
    gas_units_per_tx = 300000  # Conservative estimate
    total_gas_units = gas_units_per_tx * num_transactions
    total_cost_wei = total_gas_units * gas_price
    total_cost_eth = w3.from_wei(total_cost_wei, 'ether')
    return float(total_cost_eth)


def sponsor_gas(amount_eth: float = None) -> dict:
    """
    Transfer ETH from relayer to user wallet for gas fees
    
    Args:
        amount_eth: Amount of ETH to transfer. If None, auto-calculate based on need
    
    Returns:
        dict with transaction details
    """
    try:
        # Check balances
        user_balance = check_user_eth_balance()
        relayer_balance = check_relayer_eth_balance()
        
        logger.info(f"User ETH balance: {user_balance:.6f}")
        logger.info(f"Relayer ETH balance: {relayer_balance:.6f}")
        
        # Calculate how much ETH to send
        if amount_eth is None:
            estimated_gas = estimate_gas_needed(3)
            needed_eth = max(estimated_gas - user_balance, 0)
            
            if needed_eth <= 0:
                return {
                    "success": True,
                    "message": "User has sufficient ETH for gas",
                    "user_balance_eth": user_balance,
                    "no_transfer_needed": True
                }
            
            # Add 20% buffer
            amount_eth = needed_eth * 1.2
        
        # Safety check
        if relayer_balance < amount_eth:
            raise ValueError(f"Relayer has insufficient ETH. Has {relayer_balance}, needs {amount_eth}")
        
        # Build ETH transfer transaction
        relayer_account = Account.from_key(RELAYER_PRIVATE_KEY)
        
        nonce = w3.eth.get_transaction_count(RELAYER_ADDRESS)
        gas_price = w3.eth.gas_price
        
        tx = {
            'from': RELAYER_ADDRESS,
            'to': USER_WALLET_ADDRESS,
            'value': w3.to_wei(amount_eth, 'ether'),
            'gas': 21000,  # Standard ETH transfer
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': 1
        }
        
        # Sign and send
        signed_tx = relayer_account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get new balances
        new_user_balance = check_user_eth_balance()
        new_relayer_balance = check_relayer_eth_balance()
        
        logger.info(f"✅ Gas sponsorship successful!")
        logger.info(f"Transferred {amount_eth:.6f} ETH from relayer to user")
        logger.info(f"User new balance: {new_user_balance:.6f} ETH")
        
        return {
            "success": True,
            "message": f"Transferred {amount_eth:.6f} ETH for gas fees",
            "tx_hash": tx_hash.hex(),
            "amount_eth": amount_eth,
            "user_balance_before": user_balance,
            "user_balance_after": new_user_balance,
            "relayer_balance_before": relayer_balance,
            "relayer_balance_after": new_relayer_balance,
            "gas_cost_eth": receipt.gasUsed * gas_price / 1e18
        }
        
    except Exception as e:
        logger.error(f"Error sponsoring gas: {e}")
        raise


def auto_sponsor_if_needed() -> dict:
    """
    Automatically check and sponsor gas if user doesn't have enough
    """
    try:
        user_balance = check_user_eth_balance()
        estimated_needed = estimate_gas_needed(3)
        
        if user_balance < estimated_needed:
            logger.info(f"User needs gas sponsorship: has {user_balance:.6f}, needs ~{estimated_needed:.6f}")
            return sponsor_gas()
        else:
            return {
                "success": True,
                "message": "User has sufficient ETH",
                "user_balance_eth": user_balance,
                "no_sponsorship_needed": True
            }
    except Exception as e:
        logger.error(f"Error in auto-sponsorship: {e}")
        raise
