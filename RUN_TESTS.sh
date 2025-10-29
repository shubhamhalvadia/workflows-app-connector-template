#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════"
echo "🧪 Running Tests for Google Sheets Connector"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "📦 Building Docker image with updated tests..."
echo ""
docker build -f config/Dockerfile.dev -t workflows-connector-test .

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Docker build failed. Please check the error above."
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "🚀 Running Unit Tests (Fast, Mocked - No Setup Required)"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

docker run --rm --entrypoint python3 workflows-connector-test -m pytest tests/ -v -m "not e2e" --tb=short

TEST_EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "📊 Test Results Summary"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All unit tests passed!"
    echo ""
    echo "📝 Next Steps:"
    echo "   1. Unit tests are working correctly"
    echo "   2. To run E2E tests (requires Google OAuth token):"
    echo "      • Copy tests/env.test.example to tests/env.test"
    echo "      • Add your credentials to tests/env.test"
    echo "      • Run: docker run --rm -v \$(pwd)/tests/env.test:/usr/src/app/tests/env.test workflows-connector-test python3 -m pytest tests/test_e2e_google_sheets.py -v"
else
    echo "❌ Some tests failed. Please review the output above."
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"

exit $TEST_EXIT_CODE
