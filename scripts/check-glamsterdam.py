#!/usr/bin/env python3
"""Verify that a loaded L2 stays healthy across the local Glamsterdam fork."""

import json
import sys
import time
import urllib.request
from datetime import datetime

L1_RPC = "http://geth:8545"
SEQUENCER_RPC = "http://op-node:8547"
VERIFIER_RPC = "http://op-node-2:8547"
L2_RPC = "http://op-reth:9545"
RECIPIENT = "0x000000000000000000000000000000000000bEEF"
TIMEOUT_SECONDS = 12 * 60
MIN_TRANSFERS_EACH_SIDE = 100


def rpc(url: str, method: str, params: list | None = None):
    body = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    ).encode()
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError(f"{method}: {result['error']}")
    return result["result"]


def quantity(value: str) -> int:
    return int(value, 16)


def transfer_count() -> int:
    return quantity(rpc(L2_RPC, "eth_getBalance", [RECIPIENT, "latest"]))


def matching_heads(sequencer: dict, verifier: dict, name: str) -> bool:
    left = sequencer[name]
    right = verifier[name]
    return left["number"] == right["number"] and left["hash"] == right["hash"]


def wait_for_rpcs(deadline: float) -> None:
    while time.monotonic() < deadline:
        try:
            rpc(L1_RPC, "eth_blockNumber")
            rpc(L2_RPC, "eth_blockNumber")
            rpc(SEQUENCER_RPC, "optimism_syncStatus")
            rpc(VERIFIER_RPC, "optimism_syncStatus")
            return
        except Exception as error:  # Services start independently under Compose.
            print(f"Waiting for test RPCs: {error}", flush=True)
            time.sleep(2)
    raise TimeoutError("RPCs did not become ready")


def main() -> int:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    wait_for_rpcs(deadline)

    with open("/genesis-data/metadata/genesis.json", encoding="utf-8") as genesis_file:
        genesis = json.load(genesis_file)
    activation = genesis["config"]["amsterdamTime"]

    first_l1 = rpc(L1_RPC, "eth_getBlockByNumber", ["latest", False])
    if quantity(first_l1["timestamp"]) >= activation:
        raise RuntimeError("checker started after Amsterdam; recreate the volumes and retry")

    initial_transfers = transfer_count()
    initial_status = rpc(SEQUENCER_RPC, "optimism_syncStatus")
    initial_l2 = initial_status["unsafe_l2"]["number"]
    fork_block_number = None
    fork_l2 = None
    transfers_at_fork = None
    post_fork_blocks = 0
    last_l1 = None

    print(
        f"Watching Amsterdam activation at timestamp {activation}; "
        f"starting L1={quantity(first_l1['number'])} L2={initial_l2}",
        flush=True,
    )

    while time.monotonic() < deadline:
        l1 = rpc(L1_RPC, "eth_getBlockByNumber", ["latest", False])
        l1_number = quantity(l1["number"])
        timestamp = quantity(l1["timestamp"])
        sequencer = rpc(SEQUENCER_RPC, "optimism_syncStatus")
        verifier = rpc(VERIFIER_RPC, "optimism_syncStatus")

        if l1_number != last_l1:
            unsafe_match = matching_heads(sequencer, verifier, "unsafe_l2")
            safe_match = matching_heads(sequencer, verifier, "safe_l2")
            print(
                f"{datetime.now().strftime('%H:%M:%S')} "
                f"L1={l1_number} fork_in={activation - timestamp}s "
                f"L2={sequencer['unsafe_l2']['number']}/{verifier['unsafe_l2']['number']} "
                f"safe={sequencer['safe_l2']['number']}/{verifier['safe_l2']['number']} "
                f"heads_match={unsafe_match}/{safe_match} transfers={transfer_count()}",
                flush=True,
            )
            last_l1 = l1_number

        if timestamp >= activation:
            if not l1.get("slotNumber") or not l1.get("blockAccessListHash"):
                raise RuntimeError(
                    f"post-Amsterdam L1 block {l1_number} is missing fork header fields"
                )
            if fork_block_number is None:
                fork_block_number = l1_number
                fork_l2 = sequencer["unsafe_l2"]["number"]
                transfers_at_fork = transfer_count()
                print(
                    f"Amsterdam active in L1 block {fork_block_number}: "
                    f"slotNumber={l1['slotNumber']} "
                    f"blockAccessListHash={l1['blockAccessListHash']}",
                    flush=True,
                )
            post_fork_blocks = l1_number - fork_block_number + 1

            seq_safe_origin = sequencer["safe_l2"]["l1origin"]["number"]
            ver_safe_origin = verifier["safe_l2"]["l1origin"]["number"]
            if (
                post_fork_blocks >= 4
                and seq_safe_origin >= fork_block_number
                and ver_safe_origin >= fork_block_number
                and matching_heads(sequencer, verifier, "unsafe_l2")
                and matching_heads(sequencer, verifier, "safe_l2")
                and sequencer["unsafe_l2"]["number"] >= fork_l2 + 10
            ):
                final_transfers = transfer_count()
                before = transfers_at_fork - initial_transfers
                after = final_transfers - transfers_at_fork
                if before < MIN_TRANSFERS_EACH_SIDE:
                    raise RuntimeError(f"only {before} transfers landed before Amsterdam")
                if after < MIN_TRANSFERS_EACH_SIDE:
                    raise RuntimeError(f"only {after} transfers landed after Amsterdam")
                print(
                    "GLAMSTERDAM TRANSITION PASSED: "
                    f"fork_l1={fork_block_number}, "
                    f"unsafe_l2={sequencer['unsafe_l2']['number']}, "
                    f"safe_l2={sequencer['safe_l2']['number']}, "
                    f"safe_origin={seq_safe_origin}, "
                    f"transfers_before={before}, transfers_after={after}",
                    flush=True,
                )
                return 0

        time.sleep(3)

    raise TimeoutError("L2 did not safely derive across Amsterdam before timeout")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"GLAMSTERDAM TRANSITION FAILED: {error}", file=sys.stderr, flush=True)
        sys.exit(1)
