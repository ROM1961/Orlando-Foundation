# Token Configuration for Vault Wallet

# Supported ERC-20 Tokens on Ethereum Mainnet
TOKEN_CONFIG = {
    "ETH": {
        "name": "Ethereum",
        "symbol": "ETH",
        "decimals": 18,
        "address": None,  # Native token
        "type": "native",
        "coingecko_id": "ethereum"
    },
    "ACS": {
        "name": "ArtCubeSociety",
        "symbol": "ACS",
        "decimals": 18,
        "address": "0x1769AA7B5B4AAe76B7E6D797B379c21cAE12c46d",
        "type": "erc20",
        "price_feed": "0x359767f0CE82592eED2F13F19B0252eB539C2A2D",
        "coingecko_id": None  # Custom token
    },
    "USDC": {
        "name": "USD Coin",
        "symbol": "USDC",
        "decimals": 6,  # USDC uses 6 decimals!
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "type": "erc20",
        "coingecko_id": "usd-coin"
    },
    "USDT": {
        "name": "Tether USD",
        "symbol": "USDT",
        "decimals": 6,  # USDT uses 6 decimals!
        "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "type": "erc20",
        "coingecko_id": "tether"
    }
}

# Price feed configuration
PRICE_FEEDS = {
    "ACS": "0x359767f0CE82592eED2F13F19B0252eB539C2A2D",
    # Add more custom price feeds here if needed
}

# WalletConnect Configuration
WALLETCONNECT_CONFIG = {
    "projectId": "YOUR_WALLETCONNECT_PROJECT_ID",  # Get from https://cloud.walletconnect.com
    "chains": [1],  # Ethereum Mainnet
    "metadata": {
        "name": "Vault Wallet",
        "description": "Multi-signature DeFi Wallet with Euler V2 Integration",
        "url": "https://vault-wallet-frontend.onrender.com",
        "icons": ["https://ipfs.io/ipfs/bafkreicuf2opanzlgdcg2r3uh2jkhc64rqo75ddf6fhveuj3etkx2uhazu"]
    }
}
