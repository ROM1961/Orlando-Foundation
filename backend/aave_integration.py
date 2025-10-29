from web3 import Web3
import os
import logging
from typing import Dict, Optional
from eth_account import Account

# Aave V3 Contract Addresses (Ethereum Mainnet)
AAVE_ADDRESSES = {
    "Pool": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
    "PoolDataProvider": "0x7B4EB56E7CD4b454BA8ff71E4518426369a138a3",
}

# Minimal Aave V3 Pool ABI
AAVE_POOL_ABI = [
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "onBehalfOf", "type": "address"},
            {"name": "referralCode", "type": "uint16"}
        ],
        "name": "supply",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "to", "type": "address"}
        ],
        "name": "withdraw",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "interestRateMode", "type": "uint256"},
            {"name": "referralCode", "type": "uint16"},
            {"name": "onBehalfOf", "type": "address"}
        ],
        "name": "borrow",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "rateMode", "type": "uint256"},
            {"name": "onBehalfOf", "type": "address"}
        ],
        "name": "repay",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# ERC20 Token ABI (for approvals)
ERC20_ABI = [
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
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]

class AaveIntegration:
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.pool = w3.eth.contract(
            address=AAVE_ADDRESSES["Pool"],
            abi=AAVE_POOL_ABI
        )
    
    def build_supply_transaction(
        self, 
        asset_address: str, 
        amount: float, 
        decimals: int,
        from_address: str
    ) -> Dict:
        """Build Aave supply (lend) transaction"""
        try:
            amount_units = int(amount * (10 ** decimals))
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            transaction = self.pool.functions.supply(
                asset_address,
                amount_units,
                from_address,
                0  # referral code
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
            
            return transaction
        except Exception as e:
            logging.error(f"Error building Aave supply transaction: {e}")
            raise
    
    def build_borrow_transaction(
        self,
        asset_address: str,
        amount: float,
        decimals: int,
        from_address: str,
        interest_rate_mode: int = 2  # 1 = stable, 2 = variable
    ) -> Dict:
        """Build Aave borrow transaction"""
        try:
            amount_units = int(amount * (10 ** decimals))
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            transaction = self.pool.functions.borrow(
                asset_address,
                amount_units,
                interest_rate_mode,
                0,  # referral code
                from_address
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 400000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
            
            return transaction
        except Exception as e:
            logging.error(f"Error building Aave borrow transaction: {e}")
            raise
