"""FULL end-to-end LIVE governed run using the BUILT-IN ollama provider.

Since sovereign-agent 1.1.0, Ollama support is first-class: you bind an actor to
the shipped `ollama` provider and point it at a local model with one environment
variable. No custom provider code. A real local model PROPOSES a restock, and
the Sovereign Agent validates, COMMITS atomically, verifies, and accepts -- the
whole governed loop. Not scripted.

Run:  python demo_full_governance.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from sovereign_agent.models import Role
from sovereign_agent.organization import Organization
from reference_organizations.store import (
    CatalogEntry,
    Product,
    RestockProposal,
    apply_restock,
    below_reorder,
    record_sale,
    seed_catalog,
)

SKU = "SKU-VANILLA"

# Lucy's ice cream shop. seed_catalog needs >= 2 SKUs, each with its own
# independent stock level and reorder point (one shared till).
ICE_CREAM = (
    CatalogEntry(
        product=Product(sku="SKU-VANILLA", name="Vanilla ice cream",
                        unit_cost_cents=250, price_cents=500),
        on_hand=4, reorder_point=3,
    ),
    CatalogEntry(
        product=Product(sku="SKU-CHOCOLATE", name="Chocolate ice cream",
                        unit_cost_cents=260, price_cents=520),
        on_hand=10, reorder_point=6,
    ),
)


def main() -> int:
    # The built-in `ollama` provider reads SOVEREIGN_AGENT_LLM_MODEL (and
    # SOVEREIGN_AGENT_LLM_BASE_URL, default http://localhost:11434/v1). Point it
    # at whichever local model you pulled.
    model = os.environ.get("SOVEREIGN_DEMO_MODEL", "qwen3:latest")
    os.environ["SOVEREIGN_AGENT_LLM_MODEL"] = model

    root = Path(tempfile.mkdtemp(prefix="sovereign-full-"))
    print("=" * 74)
    print(f"SOVEREIGN AGENT — FULL governed run, built-in ollama provider, model = {model}")
    print("=" * 74)

    org = Organization.init(root)
    seed_catalog(org.db, ICE_CREAM)
    outcome = org.create_outcome(
        title="Keep the vanilla tub stocked",
        desired_state="On-hand vanilla is at or above the reorder point, the purchase is reconciled, and the replenishment is on the ledger.",
        checks=["inventory_at_or_above_reorder_point", "cash_reconciles", "replenishment_event_exists"],
        owner="principal-human",
        subject=SKU,
    )
    org.activate(outcome.id, "master-course")
    signal = record_sale(org.db, SKU, 2, 500)
    assert below_reorder(org.db), "sale should cross the reorder point"
    before = org.db.connection.execute(
        "SELECT on_hand, reorder_point FROM inventory WHERE sku=?", (SKU,)
    ).fetchone()
    on_hand, reorder = before["on_hand"], before["reorder_point"]
    print(f"\n1) Sale committed. Ledger: on_hand={on_hand}, reorder_point={reorder} (below). signal={signal.id}")

    # The built-in provider is generic: it proposes from the assignment's scope,
    # so the SOW states the real numbers the model needs to decide.
    scope = (
        f"Replenish {SKU}. Current on_hand is {on_hand}; reorder_point is {reorder}. "
        f"Propose the integer number of units to restock so on_hand reaches at least the reorder point."
    )
    sow = org.create_sow(outcome.id, scope=scope, role=Role.OPERATOR,
                         actor_id="master-course", required_effect_kind="replenishment")
    org.ready_sow(sow.id)
    assignment = org.assign(sow.id, "operator-course", "master-course")

    # Bind the actor to the SHIPPED ollama provider, then run the real governed path.
    org.rebind_actor("operator-course", "ollama", "principal-human")
    print("\n2) Actor operator-course bound to the built-in 'ollama' provider. Running the")
    print(f"   assignment — {model} reads the scope and proposes a governed ActorReport...\n")
    assignment = org.run_assignment(assignment.id)

    report_path = root / ".sovereign" / "runs" / assignment.workspace_id / ".sovereign-out" / "report.json"
    report = json.loads(report_path.read_text())
    proposed = report["proposed_restock_units"]
    print(f"3) The model's governed ActorReport: status={report['status']}, proposed={proposed} units.")
    if not proposed:
        print("   (The model did not propose a positive quantity this run — re-run, or use the")
        print("    bigger model: SOVEREIGN_DEMO_MODEL=qwen3.6:35b python demo_full_governance.py)")
        return 1

    proposal = RestockProposal(sku=SKU, quantity=proposed)
    apply_restock(org.db, proposal, assignment.id, signal.id)  # validate + commit atomically
    org.verify_outcome(outcome.id, "verifier-course")
    org.review(sow.id, "sparring-course")
    org.accept(outcome.id, "principal-human")

    after = org.db.connection.execute(
        "SELECT on_hand, reorder_point FROM inventory WHERE sku=?", (SKU,)
    ).fetchone()
    cash = org.db.connection.execute(
        "SELECT id, amount_cents FROM cash_entries ORDER BY rowid"
    ).fetchall()
    print("\n4) COMMITTED + VERIFIED + ACCEPTED.")
    print(f"   inventory now: on_hand={after['on_hand']} (>= reorder {after['reorder_point']}) — tub genuinely full")
    print(f"   cash ledger: {[(c['id'].split('_')[0], c['amount_cents']) for c in cash]}")
    print(f"\n   status: {org.status_text(outcome.id).splitlines()[0]}")
    print("\nDONE — a real local model, via sovereign-agent's built-in ollama provider,")
    print("proposed work that flowed through the FULL governance loop to an accepted outcome.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
