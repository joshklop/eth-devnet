#!/usr/bin/env python3
"""Split Glamsterdam deployment receipts into state gas and execution gas.

This targets the EIP-8037 accounting implemented by geth glamsterdam-devnet-8.
For the type-2 op-deployer transactions in this experiment, net state gas is:

    1530 * (120 * new_accounts + deployed_code_bytes + 64 * new_storage_slots)

A prestateTracer diff identifies those durable state creations. The receipt's
post-refund scalar gas is state gas + paid execution gas, so execution gas is
the remainder. Each deployment transaction in this experiment is also the sole
transaction in its block, allowing the split to be checked against Amsterdam's
block header rule: block.gas_used = max(block execution gas, block state gas).
"""

from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from pathlib import Path
from typing import Any

MAX_TX_EXECUTION_GAS = 1 << 24


def hex_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    return int(value, 16) if value.startswith("0x") else int(value)


def is_nonzero(value: str | None) -> bool:
    return hex_int(value or "0x0") != 0


class Rpc:
    def __init__(self, url: str):
        self.url = url
        self.request_id = 0

    def call(self, method: str, params: list[Any]) -> Any:
        self.request_id += 1
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": self.request_id,
            }
        ).encode()
        request = urllib.request.Request(
            self.url, body, {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.load(response)
        if "error" in payload:
            raise RuntimeError(f"{method}: {payload['error']}")
        return payload["result"]


def state_creations(diff: dict[str, Any]) -> tuple[int, int, int]:
    new_accounts = 0
    deployed_code_bytes = 0
    new_storage_slots = 0

    for address, post in diff["post"].items():
        pre = diff["pre"].get(address)
        if pre is None:
            new_accounts += 1

        old_code = (pre or {}).get("code", "0x")
        if "code" in post and post["code"] != old_code:
            deployed_code_bytes += (len(post["code"]) - 2) // 2

        old_storage = (pre or {}).get("storage", {})
        for slot, final_value in post.get("storage", {}).items():
            if is_nonzero(final_value) and not is_nonzero(old_storage.get(slot)):
                new_storage_slots += 1

    return new_accounts, deployed_code_bytes, new_storage_slots


def write_markdown(rows: list[dict[str, Any]], path: Path) -> None:
    total = sum(row["receiptGasUsed"] for row in rows)
    state = sum(row["stateGasUsed"] for row in rows)
    execution = sum(row["executionGasUsedAfterRefund"] for row in rows)
    over_cap = [row for row in rows if row["receiptGasUsed"] > MAX_TX_EXECUTION_GAS]

    lines = [
        "# Glamsterdam deployment gas dimensions",
        "",
        f"Across all {len(rows)} deployment transactions, receipt gas was **{total:,}**: "
        f"**{state:,} state gas ({state / total:.2%})** and "
        f"**{execution:,} execution gas ({execution / total:.2%})**.",
        "",
        f"All {len(over_cap)} transactions whose receipt gas exceeded the EIP-7825 "
        "16,777,216 execution-gas cap did so because of state gas. Their execution "
        "portions remained below the cap.",
        "",
        "## Transactions over 16,777,216 total gas",
        "",
        "| Phase | Description | Transaction | Receipt gas | State gas | Execution gas | State share |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in over_cap:
        lines.append(
            f"| {row['phase']} | {row['description']} | `{row['hash']}` | "
            f"{row['receiptGasUsed']:,} | {row['stateGasUsed']:,} | "
            f"{row['executionGasUsedAfterRefund']:,} | "
            f"{row['stateGasPercent']:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## All deployment transactions",
            "",
            "| Phase | Description | Nonce | Receipt gas | State gas | Execution gas | New accounts | Code bytes | New slots | Block gas | Bottleneck |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['phase']} | {row['description']} | {row['nonce']} | "
            f"{row['receiptGasUsed']:,} | {row['stateGasUsed']:,} | "
            f"{row['executionGasUsedAfterRefund']:,} | "
            f"{row['newAccounts']} | {row['deployedCodeBytes']:,} | "
            f"{row['newStorageSlots']} | {row['blockGasUsed']:,} | "
            f"{row['blockBottleneck']} |"
        )

    lines.extend(
        [
            "",
            "## Method",
            "",
            "The exact devnet-8 constants are `CPSB=1530`, 120 bytes per new "
            "account, and 64 bytes per new storage slot. Deployed runtime code is "
            "charged one state byte per code byte. The script obtains durable "
            "pre/post state with Geth's `prestateTracer` in diff mode.",
            "",
            "`executionGasUsedAfterRefund = receiptGasUsed - stateGasUsed`. This is "
            "the fee-bearing execution portion after ordinary execution-gas refunds. "
            "State gas is net of EIP-8037 state refills.",
            "",
            "Every deployment block contained one transaction. For every row, "
            "`blockGasUsed == max(stateGasUsed, executionGasUsedAfterRefund)`, "
            "independently validating the split against Amsterdam's multidimensional "
            "block accounting. All but one deployment were state-gas bottlenecked.",
            "",
        ]
    )
    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l1-rpc", default="http://127.0.0.1:8545")
    parser.add_argument(
        "--transactions-json",
        default="experiment-results/lifecycle-transactions.json",
    )
    parser.add_argument("--output-dir", default="experiment-results")
    parser.add_argument("--cost-per-state-byte", type=int, default=1530)
    parser.add_argument("--new-account-bytes", type=int, default=120)
    parser.add_argument("--new-storage-slot-bytes", type=int, default=64)
    args = parser.parse_args()

    source = json.loads(Path(args.transactions_json).read_text())
    deployments = [
        row for row in source["transactions"] if row["phase"].startswith("deploy-")
    ]
    rpc = Rpc(args.l1_rpc)
    rows: list[dict[str, Any]] = []

    for deployment in deployments:
        tx_hash = deployment["hash"]
        diff = rpc.call(
            "debug_traceTransaction",
            [
                tx_hash,
                {
                    "tracer": "prestateTracer",
                    "tracerConfig": {"diffMode": True},
                    "timeout": "120s",
                },
            ],
        )
        new_accounts, code_bytes, new_slots = state_creations(diff)
        state_bytes = (
            new_accounts * args.new_account_bytes
            + code_bytes
            + new_slots * args.new_storage_slot_bytes
        )
        state_gas = state_bytes * args.cost_per_state_byte
        receipt_gas = deployment["gasUsed"]
        execution_gas = receipt_gas - state_gas
        if execution_gas < 0:
            raise RuntimeError(
                f"reconstructed state gas exceeds receipt gas for {tx_hash}"
            )

        block = rpc.call(
            "eth_getBlockByNumber", [hex(deployment["blockNumber"]), False]
        )
        block_gas = hex_int(block["gasUsed"])
        tx_count = len(block["transactions"])
        expected_block_gas = max(state_gas, execution_gas)
        validated = tx_count == 1 and block_gas == expected_block_gas
        if not validated:
            raise RuntimeError(
                f"dimension split did not match single-tx block gas for {tx_hash}: "
                f"block={block_gas}, expected={expected_block_gas}, txs={tx_count}"
            )

        rows.append(
            {
                "phase": deployment["phase"],
                "description": deployment.get("description", deployment["phase"]),
                "hash": tx_hash,
                "nonce": deployment["nonce"],
                "blockNumber": deployment["blockNumber"],
                "transactionGasLimit": deployment["gasLimit"],
                "receiptGasUsed": receipt_gas,
                "stateGasUsed": state_gas,
                "executionGasUsedAfterRefund": execution_gas,
                "stateGasPercent": 100 * state_gas / receipt_gas,
                "exceedsEip7825ExecutionCapInTotal": receipt_gas
                > MAX_TX_EXECUTION_GAS,
                "executionWithinEip7825Cap": execution_gas
                <= MAX_TX_EXECUTION_GAS,
                "newAccounts": new_accounts,
                "deployedCodeBytes": code_bytes,
                "newStorageSlots": new_slots,
                "stateBytesCreated": state_bytes,
                "costPerStateByte": args.cost_per_state_byte,
                "blockGasUsed": block_gas,
                "blockTransactionCount": tx_count,
                "blockBottleneck": "state" if state_gas > execution_gas else "execution",
                "splitValidatedAgainstBlockGas": validated,
            }
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    total = sum(row["receiptGasUsed"] for row in rows)
    state = sum(row["stateGasUsed"] for row in rows)
    metadata = {
        "gethImageCommit": "aa1f2fcf512988eb8890d9352e601b898d6fdb2c",
        "eip": 8037,
        "costPerStateByte": args.cost_per_state_byte,
        "newAccountBytes": args.new_account_bytes,
        "newStorageSlotBytes": args.new_storage_slot_bytes,
        "eip7825ExecutionGasCap": MAX_TX_EXECUTION_GAS,
        "transactionCount": len(rows),
        "transactionsOverCapInTotalGas": sum(
            row["exceedsEip7825ExecutionCapInTotal"] for row in rows
        ),
        "totalReceiptGas": total,
        "totalStateGas": state,
        "totalExecutionGasAfterRefund": total - state,
        "stateGasPercent": 100 * state / total,
        "allSplitsValidatedAgainstBlockGas": all(
            row["splitValidatedAgainstBlockGas"] for row in rows
        ),
    }
    (output_dir / "deployment-gas-dimensions.json").write_text(
        json.dumps({"metadata": metadata, "transactions": rows}, indent=2) + "\n"
    )
    with (output_dir / "deployment-gas-dimensions.csv").open(
        "w", newline=""
    ) as output:
        writer = csv.DictWriter(
            output, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    write_markdown(rows, output_dir / "deployment-gas-dimensions.md")
    print(
        f"wrote {len(rows)} splits; total={total}, state={state} "
        f"({100 * state / total:.2f}%), execution={total - state}"
    )


if __name__ == "__main__":
    main()
