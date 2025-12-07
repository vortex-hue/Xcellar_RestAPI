#!/bin/bash

# Test all endpoints to find 500 errors
BASE_URL="http://localhost:8000/api/v1"

echo "=========================================="
echo "Testing All Endpoints for 500 Errors"
echo "=========================================="
echo ""

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local name=$3
    local data=$4
    local headers=$5
    
    if [ "$method" == "GET" ]; then
        status=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL$endpoint" $headers)
    elif [ "$method" == "POST" ]; then
        status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" $headers)
    fi
    
    if [ "$status" == "500" ]; then
        echo "❌ 500 ERROR: $name ($method $endpoint)"
        curl -s -X $method "$BASE_URL$endpoint" -H "Content-Type: application/json" ${data:+-d "$data"} $headers 2>&1 | head -5
        echo ""
    elif [ "$status" -ge 200 ] && [ "$status" -lt 300 ]; then
        echo "✓ OK ($status): $name"
    elif [ "$status" == "401" ] || [ "$status" == "403" ]; then
        echo "🔒 Auth Required ($status): $name"
    elif [ "$status" == "400" ] || [ "$status" == "404" ]; then
        echo "ℹ️  Expected ($status): $name"
    else
        echo "⚠️  Unexpected ($status): $name"
    fi
}

echo "=== PUBLIC ENDPOINTS ==="
test_endpoint "GET" "/health/" "Health Check"
test_endpoint "GET" "/marketplace/categories/" "Marketplace Categories"
test_endpoint "GET" "/marketplace/stores/" "Marketplace Stores"
test_endpoint "GET" "/marketplace/products/" "Marketplace Products"
test_endpoint "GET" "/faq/" "FAQ List"
test_endpoint "GET" "/core/banks/" "Core Banks"

echo ""
echo "=== AUTH ENDPOINTS ==="
test_endpoint "POST" "/auth/login/" "Login (invalid)" '{"email":"test@test.com","password":"test"}'
test_endpoint "POST" "/auth/register/user/" "Register User (invalid)" '{}'

echo ""
echo "=== REQUIRES AUTH ==="
test_endpoint "GET" "/orders/list/" "Orders List"
test_endpoint "GET" "/orders/available/" "Available Orders"
test_endpoint "GET" "/marketplace/cart/" "Cart"
test_endpoint "GET" "/payments/transactions/" "Transactions"
test_endpoint "GET" "/users/dashboard/" "User Dashboard"
test_endpoint "GET" "/couriers/dashboard/" "Courier Dashboard"

echo ""
echo "=== POST ENDPOINTS (no auth) ==="
test_endpoint "POST" "/help/request/" "Help Request" '{"subject":"Test","message":"Test","category":"GENERAL","user_email":"test@test.com"}'
test_endpoint "POST" "/verification/send/" "Send OTP" '{"phone_number":"+1234567890","method":"SMS"}'

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="

