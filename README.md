# A Real Agent, Governed — a live Sovereign Agent demo

> A real language model, running **on your own laptop**, helps run **Lucy's ice
> cream shop**: it makes a real tool call to look up inventory, then proposes a
> restock. A tiny "company" written in Python **checks that proposal against
> reality before it is allowed to happen** — and refuses it when it is out of
> bounds.
>
> Nothing here is scripted or faked. The model really decides. The governance
> really checks. You will watch both happen, live.

This is a hands-on companion to the **Sovereign Agent** textbook. It teaches one
idea you will use for the rest of your career with AI agents:

> ### An *actor* is not a *model*.
> A model *proposes*. A governed system *decides*. Giving a model a tool is not
> the same as giving it authority — authority stays in code you can read.

You will run three things, in order. The first is offline and always works. The
next two use a real local model.

---

## What you need (read this first)

| Requirement | Why | How to get it |
|---|---|---|
| **[uv](https://docs.astral.sh/uv/)** | installs Python 3.14 and both packages for you | `curl -LsSf https://astral.sh/uv/install.sh \| sh` — or `brew install uv` |
| **Ollama** | runs the model locally, no cloud, no API key | [ollama.com/download](https://ollama.com/download) |
| **~6 GB free disk + ~8 GB RAM** | to hold the small model | most laptops are fine |
| ~10 minutes | one-time download of the model | ☕ |

> **No API key. No internet during the demo. No account.** The model runs on
> your machine. This is the whole point: you can see there is no trick.

---

## Setup (once)

```bash
git clone https://github.com/zeroemployeeorg/sovereign-agent-live-demo.git
cd sovereign-agent-live-demo
bash setup.sh
```

`setup.sh` uses **uv** to install `sovereign-agent` and `zeocore` **from
PyPI** (exactly what you'd do in a real project — not from a source repo;
uv supplies Python 3.14 itself), checks Ollama, downloads a small model,
and warms it up.

<details>
<summary>Prefer to do it by hand? (click)</summary>

```bash
uv sync                   # sovereign-agent + zeocore, from PyPI; Python 3.14 included
ollama pull qwen3:latest  # ~5 GB, one time
```
</details>

---

## Run it — three steps

Everything below runs through `uv run`, so it always uses the environment
you just installed — no activation, same commands on macOS, Linux, and
Windows.

### Step 1 — Offline warmup (no model needed): watch a company *catch a lie*

```bash
uv run sovereign-agent demo store --mode simulated
```

This runs the full governance loop with a *scripted* actor. It ends with a
company that only accepts work when reality actually matches the claim. In the
textbook you then **break the database by hand** and re-run verification — and
the company **refuses to accept** (exit code `1`). That is the punchline:
*verification is not a rubber stamp.*

> This built-in demo is the framework's own packaged shop — it happens to sell
> tea. Steps 2 and 3 below run **Lucy's ice cream shop**, the book's running
> example. The governance is identical; only the products differ.

### Step 2 — LIVE: a real model calls a real tool, and gets governed

```bash
uv run python demo_tool_calling.py
```

A customer buys vanilla ice cream; stock drops **below** the reorder point. The
job is handed to a real local model (`qwen3:latest`). It is given **one tool**,
built with ZeoCore: `inspect_inventory`. Watch it decide to call it:

```
2) Handing the assignment to a REAL actor: qwen3:latest (local, no cloud).
   It is given ONE tool, built with ZeoCore: inspect_inventory. Watch it call it.

   qwen CALLED zeocore tool inspect_inventory({'sku': 'SKU-VANILLA'}) -> {'sku': 'SKU-VANILLA', 'on_hand': 2, 'reorder_point': 3}
   qwen SAID: RESTOCK_UNITS: 1

3) The actor PROPOSED: restock 1 units of SKU-VANILLA.

4) The Sovereign Agent does NOT trust the model. It re-validates the proposal
   against the ledger and reads the TRUE unit cost from the product record:
   VALID: 1 units x 120c (cost read from the ledger, not from qwen) = 120c.

5) Governance proof — the model's number is not authority. Try an absurd proposal:
   REFUSED: Proposed restock of 9999 exceeds the bound of 50.
```

Two things to notice:
- The **cost comes from the product record**, not from whatever the model said.
- An **absurd proposal is refused** by governed code, not by the model's good
  manners. *A provider may propose, but not without limit.*

> The exact number the model proposes can vary between runs — that's what makes
> it a real model and not a script. Governance handles whatever it proposes.

### Step 3 — LIVE: the *full* governed loop, driven by the model

```bash
uv run python demo_full_governance.py
```

This time the actor is bound to sovereign-agent's **built-in `ollama` provider**
(shipped in 1.1.0 — no custom code). The model reads the assignment and
proposes, and the proposal flows through the **entire** pipeline — assignment →
run → **atomic commit** → independent **verification** → principal
**acceptance**:

```
2) Actor operator-course bound to the built-in 'ollama' provider. Running the
   assignment — qwen3:latest reads the scope and proposes a governed ActorReport...
3) The model's governed ActorReport: status=completed, proposed=1 units.
4) COMMITTED + VERIFIED + ACCEPTED.
   inventory now: on_hand=3 (>= reorder 3) — tub genuinely full
   cash ledger: [('cash-opening', 10000), ('cash', 1000), ('cash', -250)]
   status: out_...  ACCEPTED  Keep the vanilla tub stocked
```

A real local model's proposal became a real, verified, accepted outcome — money
moved, stock is genuinely full — driven by the provider that ships in the box.

---

## How it works (the three pieces)

```
   ┌─────────────┐   "how many to restock?"   ┌──────────────────────┐
   │  qwen (LLM) │ ─────────────────────────▶ │  it decides to call  │
   │  the ACTOR  │                            │  a tool to find out  │
   └─────────────┘ ◀───────────────────────── └──────────┬───────────┘
         │            {on_hand: 2, reorder: 3}            │
         │                                                ▼
         │                                   ┌────────────────────────┐
         │  proposes: "restock N"            │  inspect_inventory      │
         │                                   │  a ZEOCORE CAPABILITY   │
         ▼                                   │  (typed, read-only)     │
   ┌───────────────────────────────────┐    └────────────────────────┘
   │  SOVEREIGN AGENT (governed Python)│
   │  • re-reads the real ledger       │   the model's number is a PROPOSAL.
   │  • reads TRUE cost from records   │   code decides what actually happens:
   │  • enforces bounds (max 50)       │   validate → commit → verify → accept
   │  • commits atomically, or REFUSES │   …or refuse.
   └───────────────────────────────────┘
```

- **The tool** — the `inspect_inventory` capability defined inline in
  `demo_tool_calling.py`. A plain Python function decorated with `@capability`
  from **ZeoCore**, with a typed request/response and a declared `READ` effect.
  The model is handed its JSON schema and may call it (Step 2).
- **The actor** — the model. It *proposes*; it cannot commit anything. In Step 2
  it's driven in-process to show a tool call; in Step 3 it's the **built-in
  `ollama` provider** that ships with sovereign-agent 1.1.0 — bind an actor to
  it with `provider = "ollama"` and one env var, no custom code.
- **The governance** — `sovereign-agent`. It re-validates every proposal against
  the real ledger, enforces limits, and only then commits — atomically — with
  independent verification and a final acceptance step.

---

## Troubleshooting

| You see… | Fix |
|---|---|
| `Python 3.14+ not found` | Install from [python.org](https://www.python.org/downloads/) or `pyenv install 3.14.3`, then re-run `setup.sh`. |
| `ollama: command not found` | Install from [ollama.com/download](https://ollama.com/download), then re-run `setup.sh`. |
| `Connection refused` on `localhost:11434` | Ollama isn't running. Open the Ollama app, or run `ollama serve` in another terminal. |
| First live run is slow (30–60 s) | Normal — the model is loading into RAM. Later runs are faster. Warm it first: `printf '' \| ollama run qwen3:latest`. |
| Laptop is low on RAM | Use the small model (default). Avoid the 35B option below. |
| Want a stronger, slower actor | `SOVEREIGN_DEMO_MODEL=qwen3.6:35b uv run python demo_tool_calling.py` (needs ~24 GB). |

Config knobs (environment variables):
- `SOVEREIGN_DEMO_MODEL` — which Ollama model to use (default `qwen3:latest`).
- `SOVEREIGN_OLLAMA_URL` — Ollama endpoint (default `http://localhost:11434/api/chat`).

---

## Where to go next

- Read `demo_tool_calling.py` — a complete ZeoCore capability, the model's
  tool-calling loop, and the governance check, side by side (~200 lines).
- Read `demo_full_governance.py` — how little it takes to bind an actor to the
  built-in `ollama` provider and run the full governed loop.
- Open the **Sovereign Agent** textbook (`sovereign-agent demo store` is
  Chapter 0) and keep going: `uvx sovereign-agent@latest doctor`.

## Files in this folder

| File | What it is |
|---|---|
| `README.md` | this guide |
| `setup.sh` | one-time setup |
| `pyproject.toml` | the two PyPI packages, pinned |
| `demo_tool_calling.py` | **Step 2** — live tool call + governance + refusal (in-process) |
| `demo_full_governance.py` | **Step 3** — full governed loop via the built-in `ollama` provider |
