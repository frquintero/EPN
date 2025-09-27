"""Run a live CCN cycle and capture prompts/responses for analysis."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import LLMClient
from worker_node import WorkerNode
from mini_ccn import MiniCCN, CCNError


@dataclass
class RoleLog:
    """Capture prompt/response data for a single role."""

    prompt: Optional[str] = None
    raw_response: Optional[str] = None
    parsed_response: Optional[str] = None


def main() -> None:
    # Allow custom query via CLI arg, else use default
    query = sys.argv[1] if len(sys.argv) > 1 else "Why is there something than nothing"

    client = LLMClient()
    worker_node = WorkerNode(client)
    ccn = MiniCCN(worker_node, debug=False)

    try:
        result = ccn.execute(query)
    except CCNError as exc:
        raise SystemExit(f"CCN execution failed: {exc}") from exc

    role_logs: Dict[str, RoleLog] = {}
    ordered_roles = []

    for event in ccn.memory.run_log:
        node_id = event.node_id
        if not node_id:
            continue
        if node_id not in role_logs:
            role_logs[node_id] = RoleLog()
        entry = role_logs[node_id]

        if event.event_type == "prompt_window":
            entry.prompt = event.data.get("prompt")
            if node_id not in ordered_roles:
                ordered_roles.append(node_id)
        elif event.event_type == "raw_response":
            entry.raw_response = event.data.get("body")
        elif event.event_type == "parsed_response":
            entry.parsed_response = event.data.get("body")

    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"live_run_{timestamp}.txt"

    final_text = result if isinstance(result, str) else json.dumps(result, indent=2)

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("CCN Live Run Capture\n")
        handle.write(f"Timestamp: {timestamp}\n")
        handle.write(f"Query: {query}\n")
        handle.write("=" * 80 + "\n\n")
        handle.write("Final Synthesis:\n")
        handle.write(final_text + "\n\n")

        for role_id in ordered_roles:
            entry = role_logs[role_id]
            handle.write("-" * 80 + "\n")
            handle.write(f"Role: {role_id}\n")
            # Show exact inputs used by this role (untrimmed, from archive)
            rec_for_role = None
            for rec in ccn.memory.archive:
                if rec.node_id == role_id:
                    rec_for_role = rec
            handle.write("Inputs (used, untrimmed):\n")
            if rec_for_role and rec_for_role.input_signals:
                try:
                    handle.write(json.dumps(rec_for_role.input_signals, indent=2, ensure_ascii=False) + "\n\n")
                except Exception:
                    for i, val in enumerate(rec_for_role.input_signals, 1):
                        handle.write(f"  Input[{i}]: {val}\n")
                    handle.write("\n")
            else:
                handle.write("<none>\n\n")
            # Raw LLM output only
            handle.write("Raw Response:\n")
            handle.write((entry.raw_response or "<missing>") + "\n\n")

        # Append roles executed as recorded in archive (source of truth)
        roles_executed = [rec.node_id for rec in ccn.memory.archive]
        handle.write(f"Roles Executed (from archive, count={len(roles_executed)}):\n")
        handle.write(json.dumps(roles_executed, indent=2, ensure_ascii=False) + "\n\n")


    print(f"Capture written to {output_path}")


if __name__ == "__main__":
    main()
