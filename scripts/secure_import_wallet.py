#!/usr/bin/env python3
"""
Secure Wallet Import Script
===========================
This script imports a wallet using a private key from environment variable.

SECURITY:
- Private key must be in environment variable (never hardcoded)
- Key is encrypted immediately using Fernet encryption
- No logging or display of raw private key
- Encrypted key stored in MongoDB

USAGE:
    export PRIVATE_KEY="0x..."
    export USER_EMAIL="your@email.com"
    export WALLET_LABEL="My Wallet"
    python3 secure_import_wallet.py
"""

import os
import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet
from eth_account import Account
import uuid
from datetime import datetime, timezone

# Security check
if len(sys.argv) > 1:
    print("❌ ERROR: Do not pass private key as command line argument!")
    print("Use environment variable instead:")
    print("  export PRIVATE_KEY='0x...'")
    sys.exit(1)

# Get configuration from environment
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'vault_wallet')
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

# Get user inputs from environment (SECURE)
PRIVATE_KEY = os.environ.get('PRIVATE_KEY')
USER_EMAIL = os.environ.get('USER_EMAIL')
WALLET_LABEL = os.environ.get('WALLET_LABEL', 'Imported Wallet')

def validate_inputs():
    """Validate all required inputs"""
    if not ENCRYPTION_KEY:
        print("❌ ERROR: ENCRYPTION_KEY not set in environment")
        print("Set it in backend/.env file")
        return False
    
    if not PRIVATE_KEY:
        print("❌ ERROR: PRIVATE_KEY not set in environment")
        print("\nUSAGE:")
        print("  export PRIVATE_KEY='0xYOUR_PRIVATE_KEY_HERE'")
        print("  export USER_EMAIL='your@email.com'")
        print("  export WALLET_LABEL='My Wallet'")
        print("  python3 secure_import_wallet.py")
        return False
    
    if not USER_EMAIL:
        print("❌ ERROR: USER_EMAIL not set in environment")
        return False
    
    # Validate private key format
    if not PRIVATE_KEY.startswith('0x'):
        print("❌ ERROR: Private key must start with '0x'")
        return False
    
    if len(PRIVATE_KEY) != 66:  # 0x + 64 hex chars
        print("❌ ERROR: Invalid private key length")
        return False
    
    return True

def encrypt_private_key(private_key: str) -> bytes:
    """Encrypt private key using Fernet"""
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    encrypted = cipher_suite.encrypt(private_key.encode())
    return encrypted

async def import_wallet():
    """Import wallet with private key"""
    
    print("=" * 60)
    print("🔐 SECURE WALLET IMPORT")
    print("=" * 60)
    
    # Validate inputs
    if not validate_inputs():
        return False
    
    print("\n📋 Configuration:")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {USER_EMAIL}")
    print(f"   Wallet Label: {WALLET_LABEL}")
    print(f"   Private Key: {'*' * 60} (hidden)")
    
    try:
        # Connect to MongoDB
        print("\n1. Connecting to database...")
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Find user
        print("2. Finding user...")
        user = await db.users.find_one({"email": USER_EMAIL})
        if not user:
            print(f"❌ ERROR: User {USER_EMAIL} not found")
            print("Please register this user first in the wallet UI")
            return False
        
        user_id = user['id']
        print(f"   ✅ User found: {user_id}")
        
        # Derive address from private key
        print("3. Deriving wallet address from private key...")
        account = Account.from_key(PRIVATE_KEY)
        wallet_address = account.address
        print(f"   ✅ Address: {wallet_address}")
        
        # Check if wallet already exists
        existing = await db.user_vaults.find_one({
            "user_id": user_id,
            "vault_address": wallet_address
        })
        
        if existing:
            print(f"\n⚠️  WARNING: Wallet {wallet_address} already imported!")
            print("   Skipping import.")
            return True
        
        # Encrypt private key
        print("4. Encrypting private key...")
        encrypted_key = encrypt_private_key(PRIVATE_KEY)
        print("   ✅ Private key encrypted")
        
        # Create vault document
        vault_id = str(uuid.uuid4())
        vault_doc = {
            "id": vault_id,
            "user_id": user_id,
            "vault_address": wallet_address,
            "label": WALLET_LABEL,
            "vault_type": "imported",
            "required_signatures": 1,
            "owner_addresses": [wallet_address],
            "private_key_encrypted": encrypted_key,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert into database
        print("5. Storing encrypted wallet in database...")
        await db.user_vaults.insert_one(vault_doc)
        print("   ✅ Wallet imported successfully!")
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"\n📝 Wallet Details:")
        print(f"   Vault ID: {vault_id}")
        print(f"   Address: {wallet_address}")
        print(f"   Label: {WALLET_LABEL}")
        print(f"\n🔒 Security:")
        print(f"   ✅ Private key encrypted with Fernet")
        print(f"   ✅ Stored securely in MongoDB")
        print(f"   ✅ Can now use wallet for transactions")
        
        print(f"\n🌐 Next Steps:")
        print(f"   1. Refresh your wallet dashboard")
        print(f"   2. Select '{WALLET_LABEL}' from vault list")
        print(f"   3. View your 9,999,000 ACS balance")
        print(f"   4. Send transactions or deploy Euler vault!")
        
        # Clean up
        await client.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function"""
    try:
        success = await import_wallet()
        
        # Clear private key from environment for security
        if 'PRIVATE_KEY' in os.environ:
            del os.environ['PRIVATE_KEY']
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Import cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
