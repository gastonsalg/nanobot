#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

IMAGE_NAME="nanobot-test"

cleanup() {
    docker rm -f nanobot-test-run 2>/dev/null || true
    docker rmi -f nanobot-test-onboarded 2>/dev/null || true
    docker rmi -f "$IMAGE_NAME" 2>/dev/null || true
}

trap cleanup EXIT

echo "=== Building Docker image ==="
docker build -t "$IMAGE_NAME" .

echo ""
echo "=== Running 'goodbot onboard' ==="
docker run --name nanobot-test-run "$IMAGE_NAME" onboard

echo ""
echo "=== Running 'goodbot status' ==="
STATUS_OUTPUT=$(docker commit nanobot-test-run nanobot-test-onboarded > /dev/null && \
    docker run --rm nanobot-test-onboarded status 2>&1) || true

echo "$STATUS_OUTPUT"

echo ""
echo "=== Validating output ==="
PASS=true

check() {
    if echo "$STATUS_OUTPUT" | grep -q "$1"; then
        echo "  PASS: found '$1'"
    else
        echo "  FAIL: missing '$1'"
        PASS=false
    fi
}

check "goodbot Status"
check "Config:"
check "Workspace:"
check "Model:"
check "OpenRouter:"
check "Anthropic:"
check "OpenAI:"

echo ""
if $PASS; then
    echo "=== All checks passed ==="
else
    echo "=== Some checks FAILED ==="
    exit 1
fi

echo ""
echo "=== Running full pytest suite in Docker ==="
docker run --rm \
    --entrypoint /bin/sh \
    -v "$(pwd)":/workspace \
    -w /workspace \
    "$IMAGE_NAME" \
    -lc "uv pip install --system --no-cache -e '.[dev]' && pytest -q"

echo ""
echo "=== Done ==="
