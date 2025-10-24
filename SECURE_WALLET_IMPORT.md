# Secure Wallet Import Guide

## ⚠️ CRITICAL SECURITY RULES

### **NEVER DO THIS:**
- ❌ Share private keys in chat/email/messages
- ❌ Paste private keys in plain text files
- ❌ Store private keys unencrypted
- ❌ Share private keys with anyone (including support/AI)
- ❌ Screenshot or photograph private keys
- ❌ Store private keys in cloud storage unencrypted

### **ALWAYS DO THIS:**
- ✅ Keep private keys offline and encrypted
- ✅ Use hardware wallets for large amounts
- ✅ Use environment variables for scripts
- ✅ Delete private keys from clipboard after use
- ✅ Use secure password managers for backups
- ✅ Test with small amounts first

---

## Method 1: Secure Script Import (RECOMMENDED)

This method keeps your private key secure by:
- Reading from environment variable (not chat/file)
- Encrypting immediately
- Never logging or displaying the key
- Storing encrypted in database

### **Steps:**

1. **Set environment variables** (private key never saved to file):
   ```bash
   export PRIVATE_KEY="0xYOUR_PRIVATE_KEY_HERE"
   export USER_EMAIL="your@email.com"
   export WALLET_LABEL="ACS Owner Wallet"
   ```

2. **Run the secure import script:**
   ```bash
   cd /app
   python3 scripts/secure_import_wallet.py
   ```

3. **Clear environment variables** (extra security):
   ```bash
   unset PRIVATE_KEY
   ```

4. **Refresh your wallet dashboard** - wallet will appear!

### **What Happens:**
- ✅ Private key read from environment
- ✅ Encrypted with Fernet (AES-128)
- ✅ Stored in MongoDB
- ✅ Original key discarded
- ✅ Can now sign transactions

---

## Method 2: Manual Database Import (Advanced)

If you prefer to do it manually in MongoDB:

1. **Generate encrypted private key**:
   ```python
   from cryptography.fernet import Fernet
   import os
   
   # Your encryption key from backend/.env
   ENCRYPTION_KEY = "899bdd1d6603b8ad056d17e3fc85eaf2346acc0b1156fb68654d46fff5b72d63"
   
   # Your private key (KEEP SECURE!)
   PRIVATE_KEY = "0xYOUR_PRIVATE_KEY"
   
   # Encrypt
   cipher = Fernet(ENCRYPTION_KEY.encode())
   encrypted = cipher.encrypt(PRIVATE_KEY.encode())
   
   print("Encrypted key (paste in MongoDB):")
   print(encrypted)
   ```

2. **Insert into MongoDB**:
   ```javascript
   db.user_vaults.updateOne(
     { "vault_address": "0xB2237eDDE60CB955053b2f072f8765717bBB96f1" },
     { $set: { "private_key_encrypted": <encrypted_key_from_step_1> } }
   )
   ```

---

## Method 3: Import via Frontend UI (Easiest)

1. Login to wallet dashboard
2. Click **"Create Vault"** button
3. Select **"Import Existing Wallet"**
4. Paste private key (encrypted in browser before sending)
5. Give it a label
6. Submit

**Security:** Private key is encrypted in browser using WebCrypto API before being sent to backend.

---

## Verify Import Successful

After importing, verify:

```bash
# Login and check vaults
curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"your_password"}' \
  | jq -r '.access_token' > /tmp/token.txt

TOKEN=$(cat /tmp/token.txt)

curl -s -X GET http://localhost:8001/api/vaults \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.[] | {label, address, can_transact: (.private_key_encrypted != null)}'
```

Should show:
```json
{
  "label": "ACS Owner Wallet",
  "address": "0xB2237eDDE60CB955053b2f072f8765717bBB96f1",
  "can_transact": true  // ✅ Has private key!
}
```

---

## Test Transaction (Small Amount First!)

Before deploying Euler vault or sending large amounts:

```bash
# Test sending 1 ACS to another address
curl -X POST http://localhost:8001/api/vaults/${VAULT_ID}/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_address": "0xTEST_ADDRESS",
    "amount": 1,
    "token": "ACS"
  }'
```

If successful, you'll get transaction hash. Verify on Etherscan!

---

## Security Best Practices

### **For Production:**

1. **Use Hardware Wallet** (Ledger/Trezor)
   - Store large amounts on hardware wallet
   - Sign transactions offline
   - Maximum security

2. **Multi-Sig Wallet** (Gnosis Safe)
   - Require multiple signatures
   - Distribute risk
   - Better for large amounts

3. **Cold Storage**
   - Keep majority of funds offline
   - Only keep operational amount hot

4. **Regular Audits**
   - Check unauthorized transactions
   - Monitor wallet activity
   - Set up alerts

### **For Development/Testing:**

1. **Separate wallets** for dev/prod
2. **Test on testnet first** (Sepolia)
3. **Small amounts** in hot wallets
4. **Regular backups** of encrypted keys

---

## Emergency Procedures

### **If Private Key Compromised:**

1. **IMMEDIATELY** transfer all funds to new wallet
2. Create new wallet with new private key
3. Update all integrations
4. Revoke all approvals on compromised wallet

### **If Forgot Password:**

- Private keys are encrypted with `ENCRYPTION_KEY`
- If you lose encryption key, funds are LOST
- **Backup encryption key securely!**

---

## Encryption Details

### **Algorithm:** Fernet (Symmetric Encryption)
- Based on AES-128 in CBC mode
- HMAC using SHA256 for authentication
- Initialization vectors are randomly generated
- Keys are URL-safe base64 encoded

### **Key Storage:**
- Encryption key in backend/.env
- Encrypted private keys in MongoDB
- No plaintext keys anywhere

### **Decryption Process:**
```python
from cryptography.fernet import Fernet

cipher = Fernet(ENCRYPTION_KEY)
private_key = cipher.decrypt(encrypted_private_key).decode()
# Use for signing transaction
# Discard immediately after use
```

---

## Frequently Asked Questions

**Q: Can you recover my private key if I lose it?**
A: No. Private keys are encrypted. If you lose both the private key AND the encryption key, funds are unrecoverable.

**Q: Is it safe to import private key via script?**
A: Yes, IF you use environment variables and run on trusted machine. Never paste in chat or files.

**Q: Should I use this for large amounts?**
A: For amounts >$10,000, consider hardware wallet or multi-sig instead.

**Q: Can others see my private key in the database?**
A: They see encrypted version only. Without encryption key, it's useless.

**Q: What if someone gets database access?**
A: They get encrypted keys. Still need encryption key to decrypt. Use strong encryption key!

---

## Summary

✅ **SECURE METHODS:**
1. Environment variable → Script import
2. Frontend UI import (encrypted in browser)
3. Manual encryption → Database insert

❌ **INSECURE METHODS:**
1. Pasting in chat/email
2. Storing in plain text files
3. Sharing with anyone
4. Screenshots/photos

**Remember:** Your private key = Your money. Protect it like your bank password!

---

## Support

Need help? Check:
- Backend logs: `/var/log/supervisor/backend.err.log`
- Script output for error messages
- Ensure all environment variables set correctly

**DO NOT** share private keys when asking for support!
