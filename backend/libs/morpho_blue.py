"""
Morpho Blue Protocol Integration
Ethereum Mainnet Contract Addresses and ABIs
"""

# Morpho Blue Core Contract
MORPHO_BLUE_ADDRESS = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"

# Morpho Blue Bundler V2 (for batch transactions)
MORPHO_BUNDLER_V2_ADDRESS = "0x4095f064b8d3c3548a3bebfd0bbfd04750e30077"

# Adaptive Curve Interest Rate Model
MORPHO_ADAPTIVE_CURVE_IRM = "0x870aC11D48B15DB9a138Cf899d20F13F79Ba00BC"

# ACS Token and Price Feed
ACS_TOKEN_ADDRESS = "0x1769AA7B5B4AAe76B7E6D797B379c21cAE12c46d"
ACS_PRICE_FEED_ADDRESS = "0x359767f0CE82592eED2F13F19B0252eB539C2A2D"

# Common token addresses
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

# Morpho Blue ABI - Core functions
MORPHO_BLUE_ABI = [
    # Supply collateral
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "loanToken", "type": "address"},
                    {"internalType": "address", "name": "collateralToken", "type": "address"},
                    {"internalType": "address", "name": "oracle", "type": "address"},
                    {"internalType": "address", "name": "irm", "type": "address"},
                    {"internalType": "uint256", "name": "lltv", "type": "uint256"}
                ],
                "internalType": "struct MarketParams",
                "name": "marketParams",
                "type": "tuple"
            },
            {"internalType": "uint256", "name": "assets", "type": "uint256"},
            {"internalType": "address", "name": "onBehalf", "type": "address"},
            {"internalType": "bytes", "name": "data", "type": "bytes"}
        ],
        "name": "supplyCollateral",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Withdraw collateral
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "loanToken", "type": "address"},
                    {"internalType": "address", "name": "collateralToken", "type": "address"},
                    {"internalType": "address", "name": "oracle", "type": "address"},
                    {"internalType": "address", "name": "irm", "type": "address"},
                    {"internalType": "uint256", "name": "lltv", "type": "uint256"}
                ],
                "internalType": "struct MarketParams",
                "name": "marketParams",
                "type": "tuple"
            },
            {"internalType": "uint256", "name": "assets", "type": "uint256"},
            {"internalType": "address", "name": "onBehalf", "type": "address"},
            {"internalType": "address", "name": "receiver", "type": "address"}
        ],
        "name": "withdrawCollateral",
        "outputs": [
            {"internalType": "uint256", "name": "assetsWithdrawn", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Borrow
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "loanToken", "type": "address"},
                    {"internalType": "address", "name": "collateralToken", "type": "address"},
                    {"internalType": "address", "name": "oracle", "type": "address"},
                    {"internalType": "address", "name": "irm", "type": "address"},
                    {"internalType": "uint256", "name": "lltv", "type": "uint256"}
                ],
                "internalType": "struct MarketParams",
                "name": "marketParams",
                "type": "tuple"
            },
            {"internalType": "uint256", "name": "assets", "type": "uint256"},
            {"internalType": "uint256", "name": "shares", "type": "uint256"},
            {"internalType": "address", "name": "onBehalf", "type": "address"},
            {"internalType": "address", "name": "receiver", "type": "address"}
        ],
        "name": "borrow",
        "outputs": [
            {"internalType": "uint256", "name": "assetsBorrowed", "type": "uint256"},
            {"internalType": "uint256", "name": "sharesBorrowed", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Repay
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "loanToken", "type": "address"},
                    {"internalType": "address", "name": "collateralToken", "type": "address"},
                    {"internalType": "address", "name": "oracle", "type": "address"},
                    {"internalType": "address", "name": "irm", "type": "address"},
                    {"internalType": "uint256", "name": "lltv", "type": "uint256"}
                ],
                "internalType": "struct MarketParams",
                "name": "marketParams",
                "type": "tuple"
            },
            {"internalType": "uint256", "name": "assets", "type": "uint256"},
            {"internalType": "uint256", "name": "shares", "type": "uint256"},
            {"internalType": "address", "name": "onBehalf", "type": "address"},
            {"internalType": "bytes", "name": "data", "type": "bytes"}
        ],
        "name": "repay",
        "outputs": [
            {"internalType": "uint256", "name": "assetsRepaid", "type": "uint256"},
            {"internalType": "uint256", "name": "sharesRepaid", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Get position
    {
        "inputs": [
            {"internalType": "bytes32", "name": "id", "type": "bytes32"},
            {"internalType": "address", "name": "user", "type": "address"}
        ],
        "name": "position",
        "outputs": [
            {"internalType": "uint256", "name": "supplyShares", "type": "uint256"},
            {"internalType": "uint128", "name": "borrowShares", "type": "uint128"},
            {"internalType": "uint128", "name": "collateral", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    # Get market info
    {
        "inputs": [
            {"internalType": "bytes32", "name": "id", "type": "bytes32"}
        ],
        "name": "market",
        "outputs": [
            {"internalType": "uint128", "name": "totalSupplyAssets", "type": "uint128"},
            {"internalType": "uint128", "name": "totalSupplyShares", "type": "uint128"},
            {"internalType": "uint128", "name": "totalBorrowAssets", "type": "uint128"},
            {"internalType": "uint128", "name": "totalBorrowShares", "type": "uint128"},
            {"internalType": "uint128", "name": "lastUpdate", "type": "uint128"},
            {"internalType": "uint128", "name": "fee", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ACS Price Feed ABI (Chainlink compatible)
ACS_PRICE_FEED_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "pure",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Default market configuration for ACS/USDC
DEFAULT_ACS_USDC_MARKET = {
    "loanToken": USDC_ADDRESS,
    "collateralToken": ACS_TOKEN_ADDRESS,
    "oracle": ACS_PRICE_FEED_ADDRESS,
    "irm": MORPHO_ADAPTIVE_CURVE_IRM,
    "lltv": int(0.75 * 1e18)  # 75% Loan-to-Value
}

# Market ID calculation helper
def calculate_market_id(market_params: dict) -> bytes:
    """
    Calculate Morpho Blue market ID from market parameters
    Market ID = keccak256(abi.encode(marketParams))
    """
    from web3 import Web3

    # Encode market params
    encoded = Web3.solidity_keccak(
        ['address', 'address', 'address', 'address', 'uint256'],
        [
            Web3.to_checksum_address(market_params['loanToken']),
            Web3.to_checksum_address(market_params['collateralToken']),
            Web3.to_checksum_address(market_params['oracle']),
            Web3.to_checksum_address(market_params['irm']),
            market_params['lltv']
        ]
    )

    return encoded
