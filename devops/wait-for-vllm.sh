#!/bin/bash
# wait-for-vllm.sh
# Waits until the vLLM server is responsive

echo "Waiting for vLLM to initialize (can take a few minutes)..."
URL="http://localhost:8000/v1/models"
MAX_ATTEMPTS=60
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $URL || echo "000")
    if [ "$HTTP_CODE" -eq 200 ]; then
        echo "vLLM is up and running!"
        exit 0
    fi
    echo "vLLM not ready yet. Attempt $((ATTEMPT+1))/$MAX_ATTEMPTS... Waiting 10s."
    sleep 10
    ATTEMPT=$((ATTEMPT+1))
done

echo "vLLM failed to initialize within timeout period."
exit 1
