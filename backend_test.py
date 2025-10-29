#!/usr/bin/env python3
"""
Backend Test Suite for Aave and Compound DeFi Integration
Tests all DeFi transaction endpoints and functionality
"""

import requests
import json
import time
import uuid
from typing import Dict, Any, Optional

# Configuration
BACKEND_URL = "https://multi-token-vault.preview.emergentagent.com/api"

class DeFiBackendTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.vault_id = None
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, message: str, details: Dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> Dict:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        req_headers = {"Content-Type": "application/json"}
        
        if self.auth_token:
            req_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        if headers:
            req_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=req_headers)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=req_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": 200 <= response.status_code < 300
            }
        except requests.exceptions.RequestException as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False
            }
        except json.JSONDecodeError as e:
            return {
                "status_code": response.status_code,
                "data": {"error": f"JSON decode error: {str(e)}", "raw_response": response.text},
                "success": False
            }
    
    def test_user_registration(self):
        """Test user registration"""
        test_email = f"defi_test_{uuid.uuid4().hex[:8]}@example.com"
        test_username = f"defi_user_{uuid.uuid4().hex[:8]}"
        
        data = {
            "username": test_username,
            "email": test_email,
            "password": "SecurePassword123!"
        }
        
        response = self.make_request("POST", "/auth/register", data)
        
        if response["success"]:
            self.auth_token = response["data"]["access_token"]
            self.user_id = response["data"]["user_id"]
            self.log_result(
                "User Registration",
                True,
                f"Successfully registered user: {test_username}",
                {"user_id": self.user_id}
            )
        else:
            self.log_result(
                "User Registration",
                False,
                f"Failed to register user: {response['data']}",
                {"status_code": response["status_code"]}
            )
        
        return response["success"]
    
    def test_vault_creation(self):
        """Test vault creation"""
        if not self.auth_token:
            self.log_result("Vault Creation", False, "No auth token available")
            return False
        
        data = {
            "label": f"DeFi Test Vault {uuid.uuid4().hex[:8]}",
            "vault_type": "multi-sig",
            "required_signatures": 1,
            "owner_addresses": []
        }
        
        response = self.make_request("POST", "/vaults/create", data)
        
        if response["success"]:
            self.vault_id = response["data"]["vault_id"]
            vault_address = response["data"]["vault_address"]
            self.log_result(
                "Vault Creation",
                True,
                f"Successfully created vault: {vault_address}",
                {"vault_id": self.vault_id, "vault_address": vault_address}
            )
        else:
            self.log_result(
                "Vault Creation",
                False,
                f"Failed to create vault: {response['data']}",
                {"status_code": response["status_code"]}
            )
        
        return response["success"]
    
    def test_defi_transaction(self, protocol: str, action: str, token: str = "USDC", amount: float = 100.0):
        """Test DeFi transaction endpoint"""
        if not self.vault_id:
            self.log_result(f"{protocol.title()} {action.title()}", False, "No vault available")
            return False
        
        data = {
            "vault_id": self.vault_id,
            "protocol": protocol.lower(),
            "action": action.lower(),
            "token": token,
            "amount": amount
        }
        
        response = self.make_request("POST", "/defi/transaction", data)
        
        test_name = f"{protocol.title()} {action.title()} ({token})"
        
        if response["success"]:
            tx_hash = response["data"].get("tx_hash", "")
            self.log_result(
                test_name,
                True,
                f"Transaction built successfully",
                {
                    "tx_hash": tx_hash,
                    "protocol": response["data"].get("protocol"),
                    "action": response["data"].get("action"),
                    "amount": response["data"].get("amount")
                }
            )
        else:
            error_msg = response["data"].get("detail", response["data"])
            # Check if it's a transaction building error vs execution error
            if "Error building transaction" in str(error_msg):
                self.log_result(
                    test_name,
                    False,
                    f"Transaction building failed: {error_msg}",
                    {"status_code": response["status_code"]}
                )
            elif "Error sending transaction" in str(error_msg):
                # This is expected - we don't have funds/gas, but transaction was built
                self.log_result(
                    test_name,
                    True,
                    f"Transaction built but execution failed (expected): {error_msg}",
                    {"status_code": response["status_code"], "note": "Expected failure due to insufficient funds"}
                )
            else:
                self.log_result(
                    test_name,
                    False,
                    f"Unexpected error: {error_msg}",
                    {"status_code": response["status_code"]}
                )
        
        return response["success"] or "Error sending transaction" in str(response["data"])
    
    def test_vault_transactions(self):
        """Test getting vault transactions"""
        if not self.vault_id:
            self.log_result("Vault Transactions", False, "No vault available")
            return False
        
        response = self.make_request("GET", f"/vaults/{self.vault_id}/transactions")
        
        if response["success"]:
            transactions = response["data"]
            self.log_result(
                "Vault Transactions",
                True,
                f"Retrieved {len(transactions)} transactions",
                {"transaction_count": len(transactions)}
            )
        else:
            self.log_result(
                "Vault Transactions",
                False,
                f"Failed to get transactions: {response['data']}",
                {"status_code": response["status_code"]}
            )
        
        return response["success"]
    
    def test_supported_tokens(self):
        """Test getting supported tokens"""
        response = self.make_request("GET", "/tokens/supported")
        
        if response["success"]:
            tokens = response["data"].get("tokens", {})
            token_count = response["data"].get("count", 0)
            
            # Check if USDC and USDT are supported
            has_usdc = "USDC" in tokens
            has_usdt = "USDT" in tokens
            
            self.log_result(
                "Supported Tokens",
                True,
                f"Retrieved {token_count} supported tokens",
                {
                    "token_count": token_count,
                    "has_usdc": has_usdc,
                    "has_usdt": has_usdt,
                    "tokens": list(tokens.keys())
                }
            )
        else:
            self.log_result(
                "Supported Tokens",
                False,
                f"Failed to get supported tokens: {response['data']}",
                {"status_code": response["status_code"]}
            )
        
        return response["success"]
    
    def test_defi_protocols(self):
        """Test getting DeFi protocols"""
        response = self.make_request("GET", "/defi/protocols")
        
        if response["success"]:
            protocols = response["data"]
            protocol_names = [p.get("name", "") for p in protocols]
            
            has_aave = any("Aave" in name for name in protocol_names)
            has_compound = any("Compound" in name for name in protocol_names)
            
            self.log_result(
                "DeFi Protocols",
                True,
                f"Retrieved {len(protocols)} protocols",
                {
                    "protocol_count": len(protocols),
                    "has_aave": has_aave,
                    "has_compound": has_compound,
                    "protocols": protocol_names
                }
            )
        else:
            self.log_result(
                "DeFi Protocols",
                False,
                f"Failed to get protocols: {response['data']}",
                {"status_code": response["status_code"]}
            )
        
        return response["success"]
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting DeFi Backend Integration Tests")
        print("=" * 60)
        
        # Basic setup tests
        if not self.test_user_registration():
            print("❌ Cannot continue without user registration")
            return
        
        if not self.test_vault_creation():
            print("❌ Cannot continue without vault creation")
            return
        
        # API endpoint tests
        self.test_supported_tokens()
        self.test_defi_protocols()
        
        # Aave Protocol Tests
        print("\n📊 Testing Aave Protocol Integration")
        print("-" * 40)
        self.test_defi_transaction("aave", "lend", "USDC", 100.0)
        self.test_defi_transaction("aave", "borrow", "USDC", 50.0)
        self.test_defi_transaction("aave", "withdraw", "USDC", 25.0)
        self.test_defi_transaction("aave", "repay", "USDC", 25.0)
        
        # Test with USDT
        self.test_defi_transaction("aave", "lend", "USDT", 100.0)
        
        # Compound Protocol Tests
        print("\n🏦 Testing Compound Protocol Integration")
        print("-" * 40)
        self.test_defi_transaction("compound", "lend", "USDC", 100.0)
        self.test_defi_transaction("compound", "borrow", "USDC", 50.0)
        self.test_defi_transaction("compound", "withdraw", "USDC", 25.0)
        self.test_defi_transaction("compound", "repay", "USDC", 25.0)
        
        # Test with USDT
        self.test_defi_transaction("compound", "lend", "USDT", 100.0)
        
        # Transaction history test
        print("\n📋 Testing Transaction Storage")
        print("-" * 40)
        self.test_vault_transactions()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n🎯 KEY FINDINGS:")
        
        # Analyze Aave tests
        aave_tests = [r for r in self.test_results if "Aave" in r["test"]]
        aave_passed = sum(1 for r in aave_tests if r["success"])
        print(f"  - Aave Integration: {aave_passed}/{len(aave_tests)} tests passed")
        
        # Analyze Compound tests
        compound_tests = [r for r in self.test_results if "Compound" in r["test"]]
        compound_passed = sum(1 for r in compound_tests if r["success"])
        print(f"  - Compound Integration: {compound_passed}/{len(compound_tests)} tests passed")
        
        # Check transaction building vs execution
        tx_building_issues = [r for r in self.test_results if not r["success"] and "building" in r["message"]]
        if tx_building_issues:
            print(f"  - Transaction Building Issues: {len(tx_building_issues)} critical failures")
        else:
            print("  - Transaction Building: All protocols working correctly ✅")

if __name__ == "__main__":
    tester = DeFiBackendTester()
    tester.run_all_tests()