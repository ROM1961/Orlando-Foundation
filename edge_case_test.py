#!/usr/bin/env python3
"""
Edge Case Tests for DeFi Integration
Tests error handling and edge cases
"""

import requests
import json
import uuid

BACKEND_URL = "https://multi-token-vault.preview.emergentagent.com/api"

def test_invalid_protocol():
    """Test with invalid protocol"""
    # First register and create vault
    test_email = f"edge_test_{uuid.uuid4().hex[:8]}@example.com"
    test_username = f"edge_user_{uuid.uuid4().hex[:8]}"
    
    # Register user
    register_data = {
        "username": test_username,
        "email": test_email,
        "password": "SecurePassword123!"
    }
    
    response = requests.post(f"{BACKEND_URL}/auth/register", json=register_data)
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.text}")
        return
    
    auth_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create vault
    vault_data = {
        "label": f"Edge Test Vault {uuid.uuid4().hex[:8]}",
        "vault_type": "multi-sig",
        "required_signatures": 1,
        "owner_addresses": []
    }
    
    response = requests.post(f"{BACKEND_URL}/vaults/create", json=vault_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Vault creation failed: {response.text}")
        return
    
    vault_id = response.json()["vault_id"]
    
    # Test invalid protocol
    invalid_data = {
        "vault_id": vault_id,
        "protocol": "invalid_protocol",
        "action": "lend",
        "token": "USDC",
        "amount": 100.0
    }
    
    response = requests.post(f"{BACKEND_URL}/defi/transaction", json=invalid_data, headers=headers)
    
    if response.status_code == 400 and "Unsupported protocol" in response.text:
        print("✅ Invalid protocol correctly rejected")
    else:
        print(f"❌ Invalid protocol test failed: {response.status_code} - {response.text}")
    
    # Test invalid action
    invalid_action_data = {
        "vault_id": vault_id,
        "protocol": "aave",
        "action": "invalid_action",
        "token": "USDC",
        "amount": 100.0
    }
    
    response = requests.post(f"{BACKEND_URL}/defi/transaction", json=invalid_action_data, headers=headers)
    
    if response.status_code == 400 and "Invalid action" in response.text:
        print("✅ Invalid action correctly rejected")
    else:
        print(f"❌ Invalid action test failed: {response.status_code} - {response.text}")
    
    # Test invalid token
    invalid_token_data = {
        "vault_id": vault_id,
        "protocol": "aave",
        "action": "lend",
        "token": "INVALID_TOKEN",
        "amount": 100.0
    }
    
    response = requests.post(f"{BACKEND_URL}/defi/transaction", json=invalid_token_data, headers=headers)
    
    if response.status_code == 400 and "Unsupported token" in response.text:
        print("✅ Invalid token correctly rejected")
    else:
        print(f"❌ Invalid token test failed: {response.status_code} - {response.text}")
    
    # Test negative amount (should work for withdraw/repay)
    negative_amount_data = {
        "vault_id": vault_id,
        "protocol": "aave",
        "action": "withdraw",
        "token": "USDC",
        "amount": -1  # Should work for max withdrawal
    }
    
    response = requests.post(f"{BACKEND_URL}/defi/transaction", json=negative_amount_data, headers=headers)
    
    # Should build transaction successfully (execution will fail due to no funds)
    if response.status_code == 500 and "insufficient funds" in response.text:
        print("✅ Negative amount (max withdrawal) correctly handled")
    else:
        print(f"❌ Negative amount test failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("🧪 Running Edge Case Tests")
    print("=" * 40)
    test_invalid_protocol()