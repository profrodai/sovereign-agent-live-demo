"""FULL end-to-end LIVE governed run: qwen (local, via Ollama) is the real
actor. It tool-calls a ZeoCore-built capability, PROPOSES a restock, and the
Sovereign Agent validates, COMMITS atomically, verifies, and accepts -- the
whole governed loop, driven by a real local model. Not scripted.

Run:  python demo_full_governance.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from sovereign_agent.providers import PROVIDERS
from sovereign_agent.providers.base import (
    InvocationRequest,
    InvocationSpec,
    ProviderCapabilities,
    ProviderEvent,
    parse_json_line,
)
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

ACTOR_SCRIPT = str(Path(__file__).resolve().parent / "ollama_actor.py")
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


class OllamaProvider:
    """A real Sovereign Agent provider backed by qwen via Ollama."""

    name = "ollama"
    executable = "python"
    requires_terminal_event = False

    def probe(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            available=True, print_mode=True, streaming=True,
            structured_result=True, workspace_write=True,
        )

    def build_invocation(self, request: InvocationRequest) -> InvocationSpec:
        return InvocationSpec(
            # sys.executable, not "python": guarantees the actor subprocess runs
            # under THIS venv (where sovereign-agent + zeocore are installed),
            # not whatever "python" happens to be on the student's PATH.
            argv=[sys.executable, ACTOR_SCRIPT, str(request.output), request.prompt],
            cwd=request.workspace,
        )

    def parse_event(self, line: str) -> ProviderEvent | None:
        return parse_json_line(line)


def main() -> int:
    PROVIDERS["ollama"] = OllamaProvider()  # runtime registration; no core edit
    root = Path(tempfile.mkdtemp(prefix="sovereign-full-"))

    model = os.environ.get("SOVEREIGN_DEMO_MODEL", "qwen3:latest")
    print("=" * 74)
    print(f"SOVEREIGN AGENT — FULL governed run, LIVE actor = {model} via Ollama")
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
    print(f"\n1) Sale committed. Ledger: on_hand={before['on_hand']}, reorder_point={before['reorder_point']} (below). signal={signal.id}")

    sow = org.create_sow(outcome.id, scope=f"Replenishment after signal {signal.id}",
                         role=Role.OPERATOR, actor_id="master-course", required_effect_kind="replenishment")
    org.ready_sow(sow.id)
    assignment = org.assign(sow.id, "operator-course", "master-course")

    # Make qwen the actor, then run the assignment through the REAL governed path.
    org.rebind_actor("operator-course", "ollama", "principal-human")
    print("\n2) Actor operator-course rebound to provider 'ollama'. Running the assignment")
    print("   (qwen tool-calls the ZeoCore inspect_inventory capability, then proposes)...\n")
    assignment = org.run_assignment(assignment.id)

    report_path = root / ".sovereign" / "runs" / assignment.workspace_id / ".sovereign-out" / "report.json"
    import json as _json
    proposed = _json.loads(report_path.read_text())["proposed_restock_units"]
    print(f"3) qwen's governed ActorReport proposed: {proposed} units.")

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
    print(f"\n4) COMMITTED + VERIFIED + ACCEPTED.")
    print(f"   inventory now: on_hand={after['on_hand']} (>= reorder {after['reorder_point']}) — tub genuinely full")
    print(f"   cash ledger: {[(c['id'].split('_')[0], c['amount_cents']) for c in cash]}")
    print(f"\n   status: {org.status_text(outcome.id).splitlines()[0]}")
    print("\nDONE — a real local LLM tool-called a ZeoCore tool and its proposal flowed")
    print("through the FULL Sovereign Agent governance loop to an accepted, verified outcome.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
