#!/bin/bash

# Comprehensive API Testing Script for Xcellar
# This script tests all major features of the API

BASE_URL="http://localhost:8000/api/v1"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to make API calls
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    local token=$5
    
    echo -e "\n${YELLOW}Testing: $description${NC}"
    echo "  $method $endpoint"
    
    local curl_cmd=(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint")
    
    # Add Content-Type for all requests (except maybe GET if strict, but API allows)
    # Actually standard is to send it.
    curl_cmd+=(-H "Content-Type: application/json")

    if [ -n "$data" ]; then
        curl_cmd+=(-d "$data")
    fi
    
    if [ -n "$token" ]; then
        curl_cmd+=(-H "Authorization: Bearer $token")
    fi
    
    response=$("${curl_cmd[@]}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        echo "$body" | python3 -m json.tool 2>/dev/null | head -10 || echo "$body" | head -5
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo "$body"
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "$body" | head -5
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "$body"
    fi
}

echo "=========================================="
echo "Xcellar API Comprehensive Test Suite"
echo "=========================================="

# 1. Health Check
echo -e "\n${YELLOW}=== 1. Health Check ===${NC}"
# Health check is at root /health/, not under /api/v1
# We use full URL to override BASE_URL prefix
response=$(curl -s -w "\n%{http_code}" -X GET "http://localhost:8000/health/")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
    echo "$body" | head -5
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
    echo "$body" | head -5
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# 2. Register Regular User
echo -e "\n${YELLOW}=== 2. User Registration ===${NC}"
TIMESTAMP=$(date +%s)
USER_EMAIL="testuser${TIMESTAMP}@example.com"
# Generate a pseudo-unique phone number ending with last 7 digits of timestamp
# Ensure it's 10 digits + country code
USER_PHONE="+123$(echo $TIMESTAMP | tail -c 8)"
if [ ${#USER_PHONE} -lt 11 ]; then
    USER_PHONE="+1234567890"
fi

USER_DATA="{
    \"email\": \"$USER_EMAIL\",
    \"phone_number\": \"$USER_PHONE\",
    \"password\": \"TestPass123!\",
    \"password_confirm\": \"TestPass123!\",
    \"full_name\": \"Test User\"
}"
test_endpoint "POST" "/auth/register/user/" "Register Regular User" "$USER_DATA" ""

# Extract user token from response
USER_TOKEN=$(curl -s -X POST "$BASE_URL/auth/register/user/" \
    -H "Content-Type: application/json" \
    -d "$USER_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('tokens', {}).get('access', ''), end='')" 2>/dev/null)

if [ -z "$USER_TOKEN" ]; then
    # Try login instead
    # Login response also has tokens nested
    USER_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login/" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$USER_EMAIL\", \"password\": \"TestPass123!\"}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('tokens', {}).get('access', ''), end='')" 2>/dev/null)
fi

# 3. Register Courier
echo -e "\n${YELLOW}=== 3. Courier Registration ===${NC}"
COURIER_EMAIL="courier${TIMESTAMP}@example.com"
COURIER_PHONE="+124$(echo $TIMESTAMP | tail -c 8)"

COURIER_DATA="{
    \"email\": \"$COURIER_EMAIL\",
    \"phone_number\": \"$COURIER_PHONE\",
    \"password\": \"TestPass123!\",
    \"password_confirm\": \"TestPass123!\",
    \"full_name\": \"Test Courier\"
}"
test_endpoint "POST" "/auth/register/courier/" "Register Courier" "$COURIER_DATA" ""

# Extract courier token
COURIER_TOKEN=$(curl -s -X POST "$BASE_URL/auth/register/courier/" \
    -H "Content-Type: application/json" \
    -d "$COURIER_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('tokens', {}).get('access', ''), end='')" 2>/dev/null)

if [ -z "$COURIER_TOKEN" ]; then
    COURIER_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login/" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$COURIER_EMAIL\", \"password\": \"TestPass123!\"}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('tokens', {}).get('access', ''), end='')" 2>/dev/null)
fi

USER_AUTH_HEADER="-H \"Authorization: Bearer $USER_TOKEN\""
COURIER_AUTH_HEADER="-H \"Authorization: Bearer $COURIER_TOKEN\""

# 4. Marketplace Endpoints
echo -e "\n${YELLOW}=== 4. Marketplace Endpoints ===${NC}"
test_endpoint "GET" "/marketplace/categories/" "List Categories" "" ""
test_endpoint "GET" "/marketplace/stores/" "List Stores" "" ""
test_endpoint "GET" "/marketplace/products/" "List Products" "" ""
test_endpoint "GET" "/marketplace/cart/" "Get Cart" "" "$USER_TOKEN"

# 5. Orders Endpoints (User)
echo -e "\n${YELLOW}=== 5. Orders Endpoints (User) ===${NC}"
test_endpoint "GET" "/orders/list/" "List Orders (User)" "" "$USER_TOKEN"

# 6. Orders Endpoints (Courier)
echo -e "\n${YELLOW}=== 6. Orders Endpoints (Courier) ===${NC}"
test_endpoint "GET" "/orders/available/" "Available Orders (Courier)" "" "$COURIER_TOKEN"

# 7. Help Endpoints
echo -e "\n${YELLOW}=== 7. Help Endpoints ===${NC}"
HELP_DATA="{
    \"subject\": \"Test Help Request\",
    \"message\": \"This is a test help request to verify the endpoint is working correctly.\",
    \"category\": \"GENERAL\",
    \"priority\": \"NORMAL\",
    \"user_email\": \"test@example.com\"
}"
test_endpoint "POST" "/help/request/" "Submit Help Request" "$HELP_DATA" ""

# 8. FAQ Endpoints
echo -e "\n${YELLOW}=== 8. FAQ Endpoints ===${NC}"
test_endpoint "GET" "/faq/" "List FAQs" "" ""

# 9. Core Endpoints
echo -e "\n${YELLOW}=== 9. Core Endpoints ===${NC}"
test_endpoint "GET" "/core/states/" "List States" "" ""

# Summary
echo -e "\n=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi



