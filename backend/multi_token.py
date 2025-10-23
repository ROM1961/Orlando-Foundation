import os
import logging
from web3 import Web3
from typing import Dict, Optional
from token_config import TOKEN_CONFIG
import requests

class MultiTokenManager:
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }
        ]
    
    def get_token_balance(self, token_symbol: str, wallet_address: str) -> float:
        """Get balance for any supported token"""
        try:
            token_info = TOKEN_CONFIG.get(token_symbol)
            if not token_info:
                logging.error(f"Unsupported token: {token_symbol}")
                return 0.0
            
            if token_info["type"] == "native":
                # ETH balance
                balance_wei = self.w3.eth.get_balance(wallet_address)
                return float(self.w3.from_wei(balance_wei, 'ether'))
            else:
                # ERC20 token balance
                contract = self.w3.eth.contract(
                    address=token_info["address"],
                    abi=self.erc20_abi
                )
                balance = contract.functions.balanceOf(wallet_address).call()
                
                # Handle different decimal places (USDC/USDT use 6 decimals)
                decimals = token_info["decimals"]
                return float(balance) / (10 ** decimals)
                
        except Exception as e:
            logging.error(f"Error getting {token_symbol} balance for {wallet_address}: {e}")
            return 0.0
    
    def get_all_balances(self, wallet_address: str) -> Dict[str, float]:
        """Get balances for all supported tokens"""
        balances = {}
        for symbol in TOKEN_CONFIG.keys():
            balances[symbol] = self.get_token_balance(symbol, wallet_address)
        return balances
    
    def get_token_price(self, token_symbol: str) -> float:
        """Get USD price for a token"""
        try:
            token_info = TOKEN_CONFIG.get(token_symbol)
            if not token_info:
                return 0.0
            
            # Stablecoins
            if token_symbol in ["USDC", "USDT"]:
                return 1.0
            
            # Custom price feed (ACS)
            if token_symbol == "ACS":
                price_feed_abi = [
                    {
                        "inputs": [],
                        "name": "getCurrentPrice",
                        "outputs": [{"internalType": "int256", "name": "", "type": "int256"}],
                        "stateMutability": "view",
                        "type": "function"
                    }
                ]
                contract = self.w3.eth.contract(
                    address=token_info["price_feed"],
                    abi=price_feed_abi
                )
                price = contract.functions.getCurrentPrice().call()
                return float(price) / 10**8
            
            # CoinGecko for others
            if token_info.get("coingecko_id"):
                response = requests.get(
                    f"https://api.coingecko.com/api/v3/simple/price",
                    params={
                        "ids": token_info["coingecko_id"],
                        "vs_currencies": "usd"
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    return float(data[token_info["coingecko_id"]]["usd"])
            
            return 0.0
            
        except Exception as e:
            logging.warning(f"Error fetching price for {token_symbol}: {e}")
            # Fallback prices
            fallback_prices = {
                "ETH": 3500.0,
                "ACS": 0.78,
                "USDC": 1.0,
                "USDT": 1.0
            }
            return fallback_prices.get(token_symbol, 0.0)
    
    def build_transfer_transaction(self, token_symbol: str, from_address: str, to_address: str, amount: float) -> Dict:
        """Build a transfer transaction for any supported token"""
        token_info = TOKEN_CONFIG.get(token_symbol)
        if not token_info:
            raise ValueError(f"Unsupported token: {token_symbol}")
        
        nonce = self.w3.eth.get_transaction_count(from_address)
        
        if token_info["type"] == "native":
            # ETH transfer
            return {
                'nonce': nonce,
                'to': to_address,
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            }
        else:
            # ERC20 transfer
            contract = self.w3.eth.contract(
                address=token_info["address"],
                abi=self.erc20_abi
            )
            
            # Calculate amount with correct decimals
            decimals = token_info["decimals"]
            amount_units = int(amount * (10 ** decimals))
            
            return contract.functions.transfer(to_address, amount_units).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
