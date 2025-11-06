"""
SushiSwap V3 Pool Integration
Handles liquidity provision and management for SushiSwap V3 pools
"""

from web3 import Web3
import os
import logging
from typing import Dict, Optional
from eth_account import Account

logger = logging.getLogger(__name__)

# SushiSwap V3 Pool Address
SUSHISWAP_V3_POOL = "0x896e639843086a9c6fa6a9776e841fe66395d5b5"

# SushiSwap V3 Pool ABI (minimal)
SUSHISWAP_POOL_ABI = [
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "fee",
        "outputs": [{"name": "", "type": "uint24"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"name": "sqrtPriceX96", "type": "uint160"},
            {"name": "tick", "type": "int24"},
            {"name": "observationIndex", "type": "uint16"},
            {"name": "observationCardinality", "type": "uint16"},
            {"name": "observationCardinalityNext", "type": "uint16"},
            {"name": "feeProtocol", "type": "uint8"},
            {"name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI for token info
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
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


class SushiSwapIntegration:
    """Manages SushiSwap V3 pool interactions"""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.pool_address = SUSHISWAP_V3_POOL
        self.pool = w3.eth.contract(
            address=Web3.to_checksum_address(SUSHISWAP_V3_POOL),
            abi=SUSHISWAP_POOL_ABI
        )
    
    def get_pool_info(self) -> Dict:
        """Get information about the SushiSwap V3 pool"""
        try:
            # Get token addresses
            token0_address = self.pool.functions.token0().call()
            token1_address = self.pool.functions.token1().call()
            
            # Get token contracts
            token0_contract = self.w3.eth.contract(address=token0_address, abi=ERC20_ABI)
            token1_contract = self.w3.eth.contract(address=token1_address, abi=ERC20_ABI)
            
            # Get token info
            token0_symbol = token0_contract.functions.symbol().call()
            token1_symbol = token1_contract.functions.symbol().call()
            token0_decimals = token0_contract.functions.decimals().call()
            token1_decimals = token1_contract.functions.decimals().call()
            
            # Get pool data
            fee = self.pool.functions.fee().call()
            liquidity = self.pool.functions.liquidity().call()
            slot0 = self.pool.functions.slot0().call()
            
            # Calculate price from sqrtPriceX96
            sqrt_price = slot0[0]
            price = (sqrt_price / (2**96)) ** 2
            
            return {
                "pool_address": self.pool_address,
                "pool_url": f"https://www.sushi.com/ethereum/pool/v3/{self.pool_address}",
                "token0": {
                    "address": token0_address,
                    "symbol": token0_symbol,
                    "decimals": token0_decimals
                },
                "token1": {
                    "address": token1_address,
                    "symbol": token1_symbol,
                    "decimals": token1_decimals
                },
                "fee_tier": fee / 10000,  # Convert to percentage
                "liquidity": str(liquidity),
                "current_price": float(price),
                "current_tick": slot0[1],
                "pair_name": f"{token0_symbol}/{token1_symbol}"
            }
            
        except Exception as e:
            logger.error(f"Error getting pool info: {e}")
            raise
    
    def get_user_position(self, wallet_address: str) -> Dict:
        """Get user's liquidity position in the pool"""
        try:
            # Note: This requires the NonfungiblePositionManager contract
            # For now, return basic info
            pool_info = self.get_pool_info()
            
            # Get user's token balances
            token0_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(pool_info["token0"]["address"]),
                abi=ERC20_ABI
            )
            token1_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(pool_info["token1"]["address"]),
                abi=ERC20_ABI
            )
            
            token0_balance = token0_contract.functions.balanceOf(wallet_address).call()
            token1_balance = token1_contract.functions.balanceOf(wallet_address).call()
            
            return {
                "wallet_address": wallet_address,
                "pool_address": self.pool_address,
                "token0_balance": token0_balance / (10 ** pool_info["token0"]["decimals"]),
                "token1_balance": token1_balance / (10 ** pool_info["token1"]["decimals"]),
                "token0_symbol": pool_info["token0"]["symbol"],
                "token1_symbol": pool_info["token1"]["symbol"]
            }
            
        except Exception as e:
            logger.error(f"Error getting user position: {e}")
            raise
