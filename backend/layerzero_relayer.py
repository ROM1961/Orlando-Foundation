"""
LayerZero Relayer Management Module
Handles relayer monitoring, balance checking, and transaction history
"""

from web3 import Web3
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
import requests

logger = logging.getLogger(__name__)

# Chain configurations
CHAIN_CONFIG = {
    "ethereum": {
        "name": "Ethereum Mainnet",
        "chain_id": 1,
        "rpc_url": os.environ.get("ETHEREUM_RPC_URL"),
        "explorer": "https://etherscan.io",
        "native_token": "ETH",
        "layerzero_endpoint": "0x66A71Dcef29A0fFBDBE3c6a460a3B5BC225Cd675"
    },
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "rpc_url": os.environ.get("BASE_RPC_URL"),
        "explorer": "https://basescan.org",
        "native_token": "ETH",
        "layerzero_endpoint": "0xb6319cC6c8c27A8F5dAF0dD3DF91EA35C4720dd7"
    },
    "solana": {
        "name": "Solana Mainnet",
        "chain_id": None,  # Solana doesn't use EVM chain IDs
        "rpc_url": os.environ.get("SOLANA_RPC_URL"),
        "explorer": "https://solscan.io",
        "native_token": "SOL",
        "layerzero_endpoint": None  # Solana uses different addressing
    }
}

class LayerZeroRelayer:
    """Manages LayerZero relayer operations and monitoring"""
    
    def __init__(self):
        self.relayer_address = os.environ.get("LAYERZERO_RELAYER_ADDRESS")
        self.relayer_private_key = os.environ.get("LAYERZERO_RELAYER_PRIVATE_KEY")
        
        # Initialize Web3 connections for EVM chains
        self.w3_connections = {}
        for chain_name, config in CHAIN_CONFIG.items():
            if config["rpc_url"] and chain_name != "solana":
                try:
                    self.w3_connections[chain_name] = Web3(Web3.HTTPProvider(config["rpc_url"]))
                    logger.info(f"Connected to {config['name']}")
                except Exception as e:
                    logger.error(f"Failed to connect to {config['name']}: {e}")
    
    def get_relayer_info(self) -> Dict:
        """Get basic relayer information"""
        return {
            "address": self.relayer_address,
            "supported_chains": list(CHAIN_CONFIG.keys()),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def get_balance_on_chain(self, chain: str) -> Dict:
        """Get relayer balance on a specific chain"""
        try:
            if chain not in CHAIN_CONFIG:
                raise ValueError(f"Unsupported chain: {chain}")
            
            config = CHAIN_CONFIG[chain]
            
            if chain == "solana":
                # Solana balance checking
                return self._get_solana_balance()
            
            # EVM chains balance checking
            if chain not in self.w3_connections:
                return {
                    "chain": chain,
                    "native_token": config["native_token"],
                    "balance": 0,
                    "balance_formatted": "0.0",
                    "error": "Not connected to chain"
                }
            
            w3 = self.w3_connections[chain]
            balance_wei = w3.eth.get_balance(self.relayer_address)
            balance_eth = w3.from_wei(balance_wei, 'ether')
            
            return {
                "chain": chain,
                "chain_name": config["name"],
                "native_token": config["native_token"],
                "balance": int(balance_wei),
                "balance_formatted": f"{float(balance_eth):.6f}",
                "address": self.relayer_address,
                "explorer_url": f"{config['explorer']}/address/{self.relayer_address}"
            }
            
        except Exception as e:
            logger.error(f"Error getting balance on {chain}: {e}")
            return {
                "chain": chain,
                "error": str(e),
                "balance": 0,
                "balance_formatted": "0.0"
            }
    
    def _get_solana_balance(self) -> Dict:
        """Get Solana balance using RPC"""
        try:
            solana_rpc = CHAIN_CONFIG["solana"]["rpc_url"]
            response = requests.post(
                solana_rpc,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [self.relayer_address]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    balance_lamports = result["result"]["value"]
                    balance_sol = balance_lamports / 1e9
                    
                    return {
                        "chain": "solana",
                        "chain_name": "Solana Mainnet",
                        "native_token": "SOL",
                        "balance": balance_lamports,
                        "balance_formatted": f"{balance_sol:.6f}",
                        "address": self.relayer_address,
                        "explorer_url": f"https://solscan.io/account/{self.relayer_address}"
                    }
            
            return {
                "chain": "solana",
                "error": "Failed to fetch Solana balance",
                "balance": 0,
                "balance_formatted": "0.0"
            }
            
        except Exception as e:
            logger.error(f"Error getting Solana balance: {e}")
            return {
                "chain": "solana",
                "error": str(e),
                "balance": 0,
                "balance_formatted": "0.0"
            }
    
    def get_all_balances(self) -> List[Dict]:
        """Get relayer balances across all chains"""
        balances = []
        for chain in CHAIN_CONFIG.keys():
            balance_info = self.get_balance_on_chain(chain)
            balances.append(balance_info)
        return balances
    
    def get_recent_transactions(self, chain: str, limit: int = 10) -> List[Dict]:
        """Get recent transactions for the relayer on a specific chain"""
        try:
            if chain not in CHAIN_CONFIG:
                return []
            
            config = CHAIN_CONFIG[chain]
            
            # For now, return mock data - in production, query block explorers or indexers
            return [
                {
                    "hash": "0x" + "0" * 64,
                    "from": self.relayer_address,
                    "to": "0x" + "1" * 40,
                    "value": "0.1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "success",
                    "chain": chain
                }
            ]
            
        except Exception as e:
            logger.error(f"Error getting transactions on {chain}: {e}")
            return []
    
    def get_relayer_status(self) -> Dict:
        """Get comprehensive relayer status"""
        balances = self.get_all_balances()
        
        # Calculate total balance in USD (simplified)
        total_eth = sum([
            float(b.get("balance_formatted", 0)) 
            for b in balances 
            if b.get("native_token") in ["ETH", "SOL"]
        ])
        
        # Check if relayer is properly funded
        is_funded = all([
            float(b.get("balance_formatted", 0)) > 0.01 
            for b in balances 
            if "error" not in b
        ])
        
        return {
            "address": self.relayer_address,
            "status": "active" if is_funded else "low_balance",
            "balances": balances,
            "total_native_balance": f"{total_eth:.6f}",
            "health": "healthy" if is_funded else "warning",
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "supported_chains": [
                {
                    "chain": chain,
                    "name": config["name"],
                    "chain_id": config.get("chain_id"),
                    "explorer": config["explorer"]
                }
                for chain, config in CHAIN_CONFIG.items()
            ]
        }
    
    def get_chain_info(self, chain: str) -> Optional[Dict]:
        """Get information about a specific chain"""
        if chain not in CHAIN_CONFIG:
            return None
        
        config = CHAIN_CONFIG[chain]
        balance_info = self.get_balance_on_chain(chain)
        
        return {
            **config,
            "current_balance": balance_info
        }


# Singleton instance
relayer = LayerZeroRelayer()
