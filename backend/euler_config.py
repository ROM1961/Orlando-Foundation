# Euler V2 Configuration and Contract Addresses

EULER_V2_CONFIG = {
    "network": "ethereum_mainnet",
    "chain_id": 1,
    
    # Core Contracts
    "contracts": {
        "EVC": "0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383",
        "EVaultFactory": "0x29a56a1b8214D9Cf7c5561811750D5cBDb45CC8e",
        "ProtocolConfig": "0xfC9200bc3a1d8b6e67c7b4C1251c9f37fE7d0E0b",
    },
    
    # Assets
    "assets": {
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "ACS": "0x1769AA7B5B4AAe76B7E6D797B379c21cAE12c46d",
    },
    
    # Oracles
    "oracles": {
        "ACS_PRICE_FEED": "0x359767f0CE82592eED2F13F19B0252eB539C2A2D",
    },
    
    # Documentation
    "docs": {
        "evc": "https://docs.euler.finance/euler-vault-kit-white-paper/ethereum-vault-connector",
        "evault": "https://docs.euler.finance/euler-vault-kit-white-paper/",
        "governance": "https://docs.euler.finance/governance/"
    }
}

# Vault deployment parameters (for future deployment)
VAULT_DEPLOYMENT_PARAMS = {
    "acs_vault": {
        "asset": "0x1769AA7B5B4AAe76B7E6D797B379c21cAE12c46d",  # ACS Token
        "oracle": "0x359767f0CE82592eED2F13F19B0252eB539C2A2D",  # ACS Price Feed
        "unit_of_account": "0x0000000000000000000000000000000000000348",  # USD
        "name": "ACS Governed Vault",
        "symbol": "eACS"
    }
}

# Known Euler V2 vaults (add more as they're deployed)
KNOWN_EULER_VAULTS = [
    # Add deployed vault addresses here
    # Example: "0x...": {"name": "WETH Vault", "asset": "WETH"}
]
