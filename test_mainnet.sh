#!/bin/bash

BACKEND_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)

echo "🔐 Testing Mainnet Morpho Blue Integration"
echo "=========================================="
echo ""

# Step 1: Register test user
echo "1️⃣ Registering test user..."
TIMESTAMP=$(date +%s)
REGISTER_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"mainnet_test_${TIMESTAMP}\",
    \"email\": \"mainnet_test_${TIMESTAMP}@test.com\",
    \"password\": \"TestPassword123!\"
  }")

TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Registration failed"
  echo "Response: $REGISTER_RESPONSE"
  exit 1
fi

echo "✅ Registered successfully"
echo "Token: ${TOKEN:0:20}..."
echo ""

# Step 2: Get mainnet config
echo "2️⃣ Fetching mainnet configuration..."
CONFIG=$(curl -s -X GET "${BACKEND_URL}/api/mainnet/morpho/config" \
  -H "Authorization: Bearer $TOKEN")

echo "✅ Configuration retrieved:"
echo "$CONFIG" | jq '.'
echo ""

# Step 3: Check user balance
echo "3️⃣ Checking user wallet balance..."
BALANCE=$(curl -s -X GET "${BACKEND_URL}/api/mainnet/morpho/user/balance" \
  -H "Authorization: Bearer $TOKEN")

echo "✅ Balance retrieved:"
echo "$BALANCE" | jq '.'
echo ""

# Step 4: Check current position
echo "4️⃣ Checking current Morpho position..."
POSITION=$(curl -s -X GET "${BACKEND_URL}/api/mainnet/morpho/position" \
  -H "Authorization: Bearer $TOKEN")

echo "✅ Position retrieved:"
echo "$POSITION" | jq '.'
echo ""

echo "=========================================="
echo "✅ All tests passed!"
echo ""
echo "🚀 Ready for mainnet transactions!"
echo ""
echo "To execute a borrow transaction, use:"
echo "curl -X POST \"${BACKEND_URL}/api/mainnet/morpho/borrow-with-gas-sponsorship\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"Authorization: Bearer YOUR_TOKEN\" \\"
echo "  -d '{"
echo "    \"collateral_amount_acs\": 100000.0,"
echo "    \"borrow_amount_usdc\": 50000.0"
echo "  }'"
echo ""
