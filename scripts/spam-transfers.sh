#!/bin/sh

set -u

RPC_URL="${RPC_URL:-http://op-reth:9545}"
PRIVATE_KEY="${PRIVATE_KEY:-0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d}"
FROM="${FROM:-0x70997970C51812dc3A010C7d01b50e0d17dc79C8}"
TO="${TO:-0x000000000000000000000000000000000000bEEF}"

until cast block-number --rpc-url "$RPC_URL" >/dev/null 2>&1; do
  echo "Waiting for L2 RPC at $RPC_URL..."
  sleep 1
done

nonce=$(cast nonce "$FROM" --block pending --rpc-url "$RPC_URL")
sent=0
failed=0
started=$(date +%s)

echo "Starting L2 transfer spam: from=$FROM nonce=$nonce block=$(cast block-number --rpc-url "$RPC_URL")"

summary() {
  now=$(date +%s)
  echo "Transfer spam stopped: sent=$sent failed=$failed elapsed=$((now - started))s"
}
trap 'summary; exit 0' INT TERM

while :; do
  if hash=$(cast send "$TO" \
    --value 1wei \
    --private-key "$PRIVATE_KEY" \
    --nonce "$nonce" \
    --gas-limit 21000 \
    --async \
    --rpc-url "$RPC_URL" 2>&1); then
    nonce=$((nonce + 1))
    sent=$((sent + 1))
    if [ $((sent % 100)) -eq 0 ]; then
      now=$(date +%s)
      block=$(cast block-number --rpc-url "$RPC_URL" 2>/dev/null || echo "?")
      echo "sent=$sent failed=$failed elapsed=$((now - started))s block=$block last=$hash"
    fi
  else
    failed=$((failed + 1))
    if [ $((failed % 10)) -eq 1 ]; then
      echo "Transfer submission failed (attempt $failed): $hash" >&2
    fi
    sleep 0.1
  fi
done
