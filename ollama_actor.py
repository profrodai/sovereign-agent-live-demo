"""Sovereign Agent actor subprocess, backed by qwen via Ollama.

The provider spawns this as: python ollama_actor.py <output_dir> <prompt>.
It writes the same report.json + artifacts.json contract the Scripted provider
writes -- but the proposed_restock_units come from a REAL local model that
tool-called a ZeoCore-built capability against the governed ledger.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so store_tool imports under the venv python

from sovereign_agent.models import ActorReport
from store_tool import run_actor


def main() -> int:
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    # output = <root>/.sovereign/runs/<wsid>/.sovereign-out  ->  root = parents[3]
    root = output.parents[3]
    db_path = root / ".sovereign" / "organization.db"

    units, transcript = run_actor(str(db_path), sku="SKU-TEA")
    for line in transcript:
        print(line, file=sys.stderr)

    report = ActorReport(
        status="completed",
        proposed_restock_units=units,
        changed_artifacts=["inventory.md"],
        proposed_checks=["inventory_at_or_above_reorder_point", "cash_reconciles"],
        questions=[],
        notes=f"qwen (local, via Ollama) tool-called a ZeoCore capability and proposed {units} units",
    )
    (output / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (output / "artifacts.json").write_text(
        '{"inventory.md": "replenishment proposed by qwen"}', encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
