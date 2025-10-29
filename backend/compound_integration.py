from web3 import Web3
import os
import logging
from typing import Dict, Optional

# Compound V3 Contract Addresses (Ethereum Mainnet)
COMPOUND_ADDRESSES = {
    "Comet_USDC": "0xc3d688B66703497DAA19211EEdff47f25384cdc3",  # USDC market
}

# Minimal Compound V3 (Comet) ABI
COMPOUND_COMET_ABI = [
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "supply",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "account", "type": "address"}
        ],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "account", "type": "address"}
        ],
        "name": "borrowBalanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
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

class CompoundIntegration:
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.comet = w3.eth.contract(
            address=COMPOUND_ADDRESSES["Comet_USDC"],
            abi=COMPOUND_COMET_ABI
        )
    
    def check_allowance(self, token_address: str, owner: str, spender: str) -> int:
        """Check ERC20 allowance for a spender"""
        try:
            token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            allowance = token_contract.functions.allowance(owner, spender).call()
            return allowance
        except Exception as e:
            logging.error(f"Error checking allowance: {e}")
            return 0
    
    def build_approval_transaction(
        self,
        token_address: str,
        spender: str,
        amount: float,
        decimals: int,
        from_address: str
    ) -> Dict:
        """Build ERC20 approval transaction"""
        try:
            token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            amount_units = int(amount * (10 ** decimals))
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            transaction = token_contract.functions.approve(
                spender,
                amount_units
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
            
            return transaction
        except Exception as e:
            logging.error(f"Error building approval transaction: {e}")
            raise
    
    def build_supply_transaction(
        self,
        asset_address: str,
        amount: float,
        decimals: int,
        from_address: str
    ) -> Dict:
        """Build Compound supply (lend) transaction"""
        try:
            amount_units = int(amount * (10 ** decimals))
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            transaction = self.comet.functions.supply(
                asset_address,
                amount_units
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 250000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
            
            return transaction
        except Exception as e:
            logging.error(f"Error building Compound supply transaction: {e}")
            raise
    
    def build_withdraw_transaction(
        self,
        asset_address: str,
        amount: float,
        decimals: int,
        from_address: str
    ) -> Dict:
        """Build Compound withdraw transaction"""
        try:
            amount_units = int(amount * (10 ** decimals))
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            transaction = self.comet.functions.withdraw(
                asset_address,
                amount_units
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 250000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
            
            return transaction
        except Exception as e:
            logging.error(f"Error building Compound withdraw transaction: {e}")
            raise
    
    def build_borrow_transaction(
        self,
        asset_address: str,
        amount: float,
        decimals: int,
        from_address: str
    ) -> Dict:
        """
        Build Compound V3 borrow transaction.
        In Compound V3, borrowing base asset (USDC) is done by withdrawing negative balance.
        """
        try:
            amount_units = int(amount * (10 ** decimals))
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            # In Compound V3, borrowing is withdrawing the base asset
            transaction = self.comet.functions.withdraw(
                asset_address,
                amount_units
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 350000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
            
            return transaction
        except Exception as e:
            logging.error(f"Error building Compound borrow transaction: {e}")
            raise
    
    def build_repay_transaction(
        self,
        asset_address: str,
        amount: float,
        decimals: int,
        from_address: str
    ) -> Dict:
        """
        Build Compound V3 repay transaction.
        In Compound V3, repaying debt is done by supplying base asset.
        """
        try:
            # Use max amount to repay all if amount is -1
            if amount == -1:
                amount_units = 2**256 - 1
            else:
                amount_units = int(amount * (10 ** decimals))
            
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            # In Compound V3, repaying is supplying the base asset
            transaction = self.comet.functions.supply(
                asset_address,
                amount_units
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
            
            return transaction
        except Exception as e:
            logging.error(f"Error building Compound repay transaction: {e}")
            raise
    
    def get_supplied_balance(self, account_address: str) -> float:
        """Get user's supplied balance in Compound"""
        try:
            balance_wei = self.comet.functions.balanceOf(account_address).call()
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logging.error(f"Error getting Compound balance: {e}")
            return 0.0
    
    def get_borrow_balance(self, account_address: str) -> float:
        """Get user's borrow balance in Compound"""
        try:
            balance_wei = self.comet.functions.borrowBalanceOf(account_address).call()
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logging.error(f"Error getting Compound borrow balance: {e}")
            return 0.0
