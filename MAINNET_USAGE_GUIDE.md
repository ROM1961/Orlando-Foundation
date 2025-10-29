# Mainnet Morpho Blue - Complete Usage Guide

## Authentication & API Access

### Step 1: Register/Login to Get JWT Token

**Option A: Register New User**
```bash
curl -X POST "https://multi-token-vault.preview.emergentagent.com/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "email": "your@email.com",
    "password": "YourPassword123!"
  }'
```

**Option B: Login Existing User**
```bash
curl -X POST "https://multi-token-vault.preview.emergentagent.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "YourPassword123!"
  }'
```

**Response (save this token):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "user_id": "abc-123-def",
  "username": "your_username"
}
```

---

## Gas-Sponsored Mainnet Endpoints (NEW!)

### These are SEPARATE from the regular Morpho endpoints:

**Regular Endpoints (testnet/user pays gas):**
- `/api/morpho/supply-collateral` ❌ Not for mainnet
- `/api/morpho/borrow` ❌ Not for mainnet

**Mainnet Gas-Sponsored Endpoints (relayer pays gas):**
- `/api/mainnet/morpho/borrow-with-gas-sponsorship` ✅ Use this!
- `/api/mainnet/morpho/supply-with-gas-sponsorship` ✅ Use this!

---

## Complete Usage Examples

### Example 1: Check Configuration
```bash
curl -X GET "https://multi-token-vault.preview.emergentagent.com/api/mainnet/morpho/config" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

### Example 2: Check Your Balance
```bash
curl -X GET "https://multi-token-vault.preview.emergentagent.com/api/mainnet/morpho/user/balance" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

**Response:**
```json
{
  "user_address": "0xB2237eDDE60CB955053b2f072f8765717bBB96f1",
  "acs_balance": 9900000.0,
  "usdc_balance": 0.0
}
```

### Example 3: Supply ACS Collateral (Gas-Sponsored)
```bash
curl -X POST "https://multi-token-vault.preview.emergentagent.com/api/mainnet/morpho/supply-with-gas-sponsorship" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -d '{
    "amount_acs": 100000.0
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully supplied 100000.0 ACS as collateral",
  "approval_tx_hash": "0xabc123...",
  "supply_tx_hash": "0xdef456...",
  "borrow_tx_hash": null,
  "gas_paid_by": "0x2a98A48f2f9caFe51fc3951C57fC6014943E0125",
  "total_gas_cost_eth": "0.012345"
}
```

### Example 4: Borrow USDC (Gas-Sponsored) - COMPLETE FLOW
```bash
curl -X POST "https://multi-token-vault.preview.emergentagent.com/api/mainnet/morpho/borrow-with-gas-sponsorship" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -d '{
    "collateral_amount_acs": 100000.0,
    "borrow_amount_usdc": 50000.0
  }'
```

**This single call does:**
1. ✅ Approves ACS spending (if needed)
2. ✅ Supplies ACS collateral
3. ✅ Borrows USDC
4. ✅ Relayer pays ALL gas fees

**Response:**
```json
{
  "success": true,
  "message": "Successfully borrowed 50000.0 USDC using 100000.0 ACS collateral",
  "approval_tx_hash": "0xabc123...",
  "supply_tx_hash": "0xdef456...",
  "borrow_tx_hash": "0xghi789...",
  "gas_paid_by": "0x2a98A48f2f9caFe51fc3951C57fC6014943E0125",
  "total_gas_cost_eth": "0.045678"
}
```

### Example 5: Check Your Position
```bash
curl -X GET "https://multi-token-vault.preview.emergentagent.com/api/mainnet/morpho/position" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

**Response:**
```json
{
  "user_address": "0xB2237eDDE60CB955053b2f072f8765717bBB96f1",
  "supply_shares": 0,
  "borrow_shares": 50000000000,
  "collateral": 100000000000000000000000,
  "collateral_formatted_acs": 100000.0,
  "borrow_formatted_usdc": 50000.0
}
```

---

## UI Access

**Dashboard URL:**
https://multi-token-vault.preview.emergentagent.com

**Features:**
- Login/Register
- Create vaults
- View balances
- DeFi Protocols tab (Aave, Compound)
- **Bridge tab** (LayerZero Relayer monitoring)
- Morpho Blue tab (existing supply/borrow UI)

**Note:** The UI currently uses the testnet Morpho endpoints. For mainnet gas-sponsored transactions, you need to use the API directly (as shown above).

---

## How Gas Sponsorship Works

### Traditional Flow (User Pays Gas):
```
User → Signs & Sends TX → Network → User's ETH pays gas
```

### Gas-Sponsored Flow (Relayer Pays):
```
1. User signs TX with their private key (stored in backend)
2. Backend sends signed TX to network
3. Relayer's ETH pays for gas
4. User receives USDC without spending ETH!
```

**Key Points:**
- Your wallet private key is used for signing
- Relayer's wallet pays gas fees
- You keep full control of your funds
- No ETH needed in your wallet!

---

## Quick Start Script

```bash
#!/bin/bash

# 1. Login and get token
TOKEN=$(curl -s -X POST "https://multi-token-vault.preview.emergentagent.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"YourPassword123!"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# 2. Check balance
curl -X GET "https://multi-token-vault.preview.emergentagent.com/api/mainnet/morpho/user/balance" \
  -H "Authorization: Bearer $TOKEN"

# 3. Execute borrow (supply 100k ACS, borrow 50k USDC)
curl -X POST "https://multi-token-vault.preview.emergentagent.com/api/mainnet/morpho/borrow-with-gas-sponsorship" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "collateral_amount_acs": 100000.0,
    "borrow_amount_usdc": 50000.0
  }'

# 4. Check position
curl -X GET "https://multi-token-vault.preview.emergentagent.com/api/mainnet/morpho/position" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Testing Recommendations

### Test 1: Small Amount
```json
{
  "collateral_amount_acs": 1000.0,
  "borrow_amount_usdc": 500.0
}
```

### Test 2: Medium Amount
```json
{
  "collateral_amount_acs": 50000.0,
  "borrow_amount_usdc": 25000.0
}
```

### Test 3: Large Amount (Your full balance)
```json
{
  "collateral_amount_acs": 9900000.0,
  "borrow_amount_usdc": 4950000.0
}
```

---

## Troubleshooting

**Error: "Unauthorized" or "Invalid token"**
- Re-login to get a fresh JWT token
- Make sure to include `Authorization: Bearer` prefix

**Error: "Insufficient balance"**
- Check balance with `/api/mainnet/morpho/user/balance`
- Verify ACS token amount in your wallet

**Error: "Execution reverted"**
- Check LTV ratio (max 75%)
- Ensure you're not borrowing too much

**Success but no USDC received?**
- Check transaction hash on Etherscan
- Verify transaction was mined
- Check USDC balance in your wallet

---

## Support

If you encounter issues:
1. Check backend logs: `tail -f /var/log/supervisor/backend.err.log`
2. Verify configuration: `GET /api/mainnet/morpho/config`
3. Test with small amounts first
4. Check transaction hashes on Etherscan

**Ready to execute your first mainnet borrow!** 🚀
