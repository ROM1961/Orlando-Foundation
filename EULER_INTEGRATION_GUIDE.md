# Euler V2 Integration Guide

## Overview

This guide explains the Euler V2 integration in your Vault Wallet and what additional steps are needed for full deployment.

## ✅ What's Integrated

### Backend Integration
- **euler_integration.py**: Python module to interact with Euler V2 contracts
- **euler_config.py**: Configuration file with all Euler V2 addresses
- **API endpoints**: New endpoints to query Euler vault data

### Core Functionality
- View Euler vault balances
- Check account collaterals
- Monitor health factors
- Query vault liquidity
- Validate Euler vaults

### Existing Euler V2 Contracts (Mainnet)
- **EVC**: `0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383`
- **EVault Factory**: `0x29a56a1b8214D9Cf7c5561811750D5cBDb45CC8e`
- **Protocol Config**: `0xfC9200bc3a1d8b6e67c7b4C1251c9f37fE7d0E0b`

## ⚠️ What Requires Deployment

The following components would need to be deployed separately (requires wallet with ETH for gas):

### 1. ACS Token Vault (EVault)
**Purpose**: Create a governed vault for ACS token deposits

**Deployment Steps**:
```javascript
// Using Euler EVault Factory
const factory = new ethers.Contract(
  "0x29a56a1b8214D9Cf7c5561811750D5cBDb45CC8e",
  EVaultFactoryABI,
  signer
);

const tx = await factory.createProxy(
  "0x1769AA7B5B4AAe76B7E6D797B379c21cAE12c46d", // ACS token
  true, // Upgradeable
  "0x..." // Init data
);
```

**Cost**: ~0.05-0.1 ETH for deployment

### 2. Custom Price Adapter
**Purpose**: Adapter to use your ACS price feed with Euler oracle system

**Required**:
- Implement IPriceOracle interface
- Connect to ACS_PRICE_FEED (0x359767...2A2D)
- Deploy contract
- Verify on Etherscan

**Cost**: ~0.02-0.05 ETH

### 3. Interest Rate Model (Linear Kink IRM)
**Purpose**: Define interest rates for ACS vault

**Deployment**:
```solidity
// Deploy LinearKinkIRM with your parameters
LinearKinkIRM irm = new LinearKinkIRM(
    baseRate,      // e.g., 2%
    kinkRate,      // e.g., 10%
    maxRate,       // e.g., 100%
    kinkUtilization // e.g., 80%
);
```

**Cost**: ~0.02-0.04 ETH

### 4. Governance Setup
**Purpose**: Configure vault governance parameters

**Steps**:
1. Deploy Governor contract or use existing
2. Set vault parameters (collateral factor, borrow factor, etc.)
3. Configure fee recipient
4. Set caps (supply cap, borrow cap)

**Cost**: ~0.05-0.1 ETH

## 📊 Current Features (Read-Only)

### Available API Endpoints

```bash
# Get Euler vault information
GET /api/euler/vaults/{vault_address}/info?account={account_address}

# Get account's Euler collaterals
GET /api/euler/accounts/{account_address}/collaterals

# Check vault health
GET /api/euler/vaults/{vault_address}/health?account={account_address}
```

### Frontend Features
- View Euler vault balances
- Monitor collateral positions
- Check health factors
- Track vault APYs (if available)

## 🚀 Deployment Workflow

If you want to deploy the full Euler V2 integration:

### Prerequisites
1. Ethereum wallet with ~0.5 ETH for gas
2. Hardhat/Foundry development environment
3. Alchemy/Infura RPC endpoint (you have this)
4. Etherscan API key (you have this)

### Step-by-Step Deployment

#### 1. Set up development environment
```bash
npm install --save-dev hardhat @openzeppelin/contracts
npx hardhat init
```

#### 2. Deploy Price Adapter
```bash
npx hardhat run scripts/deploy-price-adapter.js --network mainnet
```

#### 3. Deploy IRM
```bash
npx hardhat run scripts/deploy-irm.js --network mainnet
```

#### 4. Create ACS Vault
```bash
npx hardhat run scripts/create-acs-vault.js --network mainnet
```

#### 5. Verify Contracts
```bash
npx hardhat verify --network mainnet DEPLOYED_ADDRESS "constructor" "args"
```

#### 6. Configure Governance
```bash
npx hardhat run scripts/setup-governance.js --network mainnet
```

## 📝 Testing Without Deployment

You can test the integration with existing Euler vaults:

### 1. Find Existing Euler Vaults
- Visit https://app.euler.finance/
- Browse available vaults
- Copy vault addresses

### 2. Add to Configuration
Edit `euler_config.py`:
```python
KNOWN_EULER_VAULTS = [
    {
        "address": "0x...",
        "name": "WETH Vault",
        "asset": "WETH"
    }
]
```

### 3. Test API
```bash
curl https://vault-wallet-backend.onrender.com/api/euler/vaults/0x.../info?account=0x...
```

## 🔗 Useful Resources

- **Euler Finance Docs**: https://docs.euler.finance/
- **EVK White Paper**: https://docs.euler.finance/euler-vault-kit-white-paper/
- **GitHub**: https://github.com/euler-xyz
- **Discord**: https://discord.gg/euler
- **Etherscan**: https://etherscan.io/address/0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383

## 💡 Next Steps

### Immediate (No Deployment Needed)
1. ✅ Test with existing Euler vaults
2. ✅ Add Euler vault viewing in frontend
3. ✅ Monitor health factors

### Future (Requires Deployment)
1. Deploy ACS price adapter contract
2. Deploy Linear Kink IRM
3. Create ACS governed vault via factory
4. Set up governance parameters
5. Verify all contracts on Etherscan
6. Enable deposits/withdrawals in UI

## ⚡ Estimated Costs

| Component | Gas Cost | ETH (@ 30 gwei) |
|-----------|----------|------------------|
| Price Adapter | ~500k gas | ~0.015 ETH |
| Linear IRM | ~400k gas | ~0.012 ETH |
| Vault Creation | ~1M gas | ~0.030 ETH |
| Governance Setup | ~300k gas | ~0.009 ETH |
| Verifications | Free | Free |
| **Total** | **~2.2M gas** | **~0.066 ETH** |

Add ~20% buffer for gas price fluctuations = **~0.08 ETH total**

## 🛡️ Security Considerations

1. **Audit**: Custom contracts should be audited before mainnet deployment
2. **Testing**: Deploy on Sepolia testnet first
3. **Governance**: Use multi-sig for vault governance
4. **Parameters**: Start conservative (low caps, high collateral factors)
5. **Monitoring**: Set up alerts for health factors and liquidations

## 📞 Support

For Euler V2 specific questions:
- Euler Discord: https://discord.gg/euler
- Documentation: https://docs.euler.finance/
- GitHub Issues: https://github.com/euler-xyz/euler-vault-kit
