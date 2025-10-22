from web3 import Web3
import os
import logging
from typing import Dict, List, Optional

# Euler V2 Contract Addresses
EULER_ADDRESSES = {
    "EVC": "0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383",
    "EVaultFactory": "0x29a56a1b8214D9Cf7c5561811750D5cBDb45CC8e",
    "ProtocolConfig": "0xfC9200bc3a1d8b6e67c7b4C1251c9f37fE7d0E0b",
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
}

# Minimal ABIs for Euler V2 contracts
EVC_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "getAccountOwner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "getCollaterals",
        "outputs": [{"name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

EVAULT_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "asset",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "accountLiquidity",
        "outputs": [
            {"name": "collateralValue", "type": "uint256"},
            {"name": "liabilityValue", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

EVAULT_FACTORY_ABI = [
    {
        "inputs": [{"name": "vault", "type": "address"}],
        "name": "isValidVault",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class EulerV2Integration:
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.evc = w3.eth.contract(
            address=EULER_ADDRESSES["EVC"],
            abi=EVC_ABI
        )
        self.evault_factory = w3.eth.contract(
            address=EULER_ADDRESSES["EVaultFactory"],
            abi=EVAULT_FACTORY_ABI
        )
        
    def get_account_collaterals(self, account_address: str) -> List[str]:
        """Get list of collateral vaults for an account"""
        try:
            collaterals = self.evc.functions.getCollaterals(account_address).call()
            return collaterals
        except Exception as e:
            logging.error(f"Error getting collaterals for {account_address}: {e}")
            return []
    
    def get_vault_balance(self, vault_address: str, account_address: str) -> float:
        """Get account balance in a specific Euler vault"""
        try:
            vault = self.w3.eth.contract(address=vault_address, abi=EVAULT_ABI)
            balance_wei = vault.functions.balanceOf(account_address).call()
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logging.error(f"Error getting vault balance: {e}")
            return 0.0
    
    def get_vault_asset(self, vault_address: str) -> Optional[str]:
        """Get underlying asset address for a vault"""
        try:
            vault = self.w3.eth.contract(address=vault_address, abi=EVAULT_ABI)
            asset = vault.functions.asset().call()
            return asset
        except Exception as e:
            logging.error(f"Error getting vault asset: {e}")
            return None
    
    def get_account_liquidity(self, vault_address: str, account_address: str) -> Dict:
        """Get account liquidity metrics (collateral and liability)"""
        try:
            vault = self.w3.eth.contract(address=vault_address, abi=EVAULT_ABI)
            collateral, liability = vault.functions.accountLiquidity(account_address).call()
            return {
                "collateral_value": float(self.w3.from_wei(collateral, 'ether')),
                "liability_value": float(self.w3.from_wei(liability, 'ether')),
                "health_factor": float(collateral / liability) if liability > 0 else float('inf')
            }
        except Exception as e:
            logging.error(f"Error getting account liquidity: {e}")
            return {
                "collateral_value": 0.0,
                "liability_value": 0.0,
                "health_factor": 0.0
            }
    
    def is_valid_vault(self, vault_address: str) -> bool:
        """Check if address is a valid Euler vault"""
        try:
            return self.evault_factory.functions.isValidVault(vault_address).call()
        except Exception as e:
            logging.error(f"Error checking vault validity: {e}")
            return False
    
    def get_vault_info(self, vault_address: str, account_address: str) -> Dict:
        """Get comprehensive vault information for an account"""
        try:
            balance = self.get_vault_balance(vault_address, account_address)
            asset = self.get_vault_asset(vault_address)
            liquidity = self.get_account_liquidity(vault_address, account_address)
            is_valid = self.is_valid_vault(vault_address)
            
            return {
                "vault_address": vault_address,
                "is_valid": is_valid,
                "balance": balance,
                "asset_address": asset,
                "collateral_value": liquidity["collateral_value"],
                "liability_value": liquidity["liability_value"],
                "health_factor": liquidity["health_factor"]
            }
        except Exception as e:
            logging.error(f"Error getting vault info: {e}")
            return {}
