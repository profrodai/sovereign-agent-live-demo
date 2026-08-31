"""The ZeoCore-built tool + the qwen tool-calling loop, shared by the actor
subprocess and the demo driver."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import urllib.request

from pydantic import BaseModel

from zeo_core.tools import ToolContext, bound_capability_of, capability
from zeo_core.tools.invoke import invoke_sync
from zeo_core.contracts import CapabilityResult
from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.capabilities.metadata import CapabilityExample

import os

# Configurable so this runs on any laptop. Defaults to a small, laptop-sized
# model; set SOVEREIGN_DEMO_MODEL=qwen3.6:35b on a big machine for a stronger actor.
MODEL = os.environ.get("SOVEREIGN_DEMO_MODEL", "qwen3:latest")
OLLAMA = os.environ.get("SOVEREIGN_OLLAMA_URL", "http://localhost:11434/api/chat")


class InspectInventoryRequest(BaseModel):
    sku: str


class InspectInventoryResponse(BaseModel):
    sku: str
    on_hand: int
    reorder_point: int


@capability(
    id="store.inspect_inventory@1.0.0",
    description="Read the CURRENT on_hand and reorder_point for a store SKU from the governed ledger. Call this before proposing a restock; never guess stock levels.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            request={"sku": "SKU-TEA"},
            response={"sku": "SKU-TEA", "on_hand": 2, "reorder_point": 3},
        ),
    ),
)
def inspect_inventory(
    request: InspectInventoryRequest, ctx: ToolContext
) -> CapabilityResult[InspectInventoryResponse]:
    db_path = ctx.metadata["db_path"]
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT on_hand, reorder_point FROM inventory WHERE sku = ?", (request.sku,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return CapabilityResult.fail(msg=f"unknown sku {request.sku}", code="NO_SKU")
    return CapabilityResult.ok(
        data=InspectInventoryResponse(
            sku=request.sku, on_hand=int(row["on_hand"]), reorder_point=int(row["reorder_point"])
        )
    )


CAP = bound_capability_of(inspect_inventory)


def _ctx(db_path: str) -> ToolContext:
    return ToolContext(
        run_id="live-demo",
        tool_name="inspect_inventory",
        tool_version="1.0.0",
        logger=logging.getLogger("live-demo"),
        fs=None,
        work_dir=".",
        output_dir=".",
        metadata={"db_path": db_path},
    )


def _chat(messages: list[dict], tools: list[dict]) -> dict:
    req = {"model": MODEL, "messages": messages, "tools": tools, "stream": False}
    r = urllib.request.urlopen(
        urllib.request.Request(
            OLLAMA, data=json.dumps(req).encode(), headers={"Content-Type": "application/json"}
        ),
        timeout=600,
    )
    return json.load(r)["message"]


def run_actor(db_path: str, sku: str = "SKU-TEA") -> tuple[int, list[str]]:
    """qwen decides a restock quantity by calling the ZeoCore tool. Returns (units, transcript)."""
    ctx = _ctx(db_path)
    tool_schema = {
        "type": "function",
        "function": {
            "name": "inspect_inventory",
            "description": CAP.definition.description,
            "parameters": CAP.request_model.model_json_schema(),
        },
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You are a Sovereign Agent store operator actor. You PROPOSE; you do not "
                "commit. You MUST call inspect_inventory to learn real stock before proposing. "
                f"Goal: keep {sku} at or ABOVE its reorder point. When ready, reply with exactly "
                "one line: RESTOCK_UNITS: <integer>."
            ),
        },
        {"role": "user", "content": f"Keep {sku} stocked at or above its reorder point. How many units should we order?"},
    ]
    transcript: list[str] = []
    for _turn in range(6):
        msg = _chat(messages, [tool_schema])
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if calls:
            for call in calls:
                fn = call["function"]
                args = fn["arguments"]
                if isinstance(args, str):
                    args = json.loads(args)
                result = invoke_sync(CAP, InspectInventoryRequest(**args), ctx)
                payload = result.data.model_dump() if result.ok else {"error": result.msg}
                transcript.append(
                    f"qwen CALLED zeocore tool inspect_inventory({args}) -> {payload}"
                )
                messages.append(
                    {"role": "tool", "content": json.dumps(payload), "tool_name": fn["name"]}
                )
            continue
        content = msg.get("content") or ""
        transcript.append(f"qwen SAID: {content.strip()[:200]}")
        m = re.search(r"RESTOCK_UNITS:\s*(\d+)", content) or re.search(r"\b(\d{1,3})\b", content)
        if m:
            return int(m.group(1)), transcript
        messages.append({"role": "user", "content": "Reply with exactly: RESTOCK_UNITS: <integer>."})
    raise RuntimeError("qwen never produced a RESTOCK_UNITS proposal")
