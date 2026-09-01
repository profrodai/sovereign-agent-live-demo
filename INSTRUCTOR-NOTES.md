# Instructor notes — live Sovereign Agent demo (ITAM)

Student-facing guide is `README.md`. This file is just for you: timing, talking
points, and what to do if the room's laptops fight back. **Verified end-to-end
on 2026-08-31** against `sovereign-agent==1.0.0` + `zeocore==0.5.0` from PyPI, in
a clean venv, with the small model `qwen3:latest`.

## Before class
- On the projector machine, run `bash setup.sh` once and warm the model.
- Tell students to run `bash setup.sh` at home (the model download is the slow
  part — don't do 30 downloads live on the ITAM wifi). If they can't, they can
  still watch and do **Step 1** (offline) live.
- Have the offline Step 1 ready as the guaranteed-green fallback.

## The one sentence they should leave with
> **An actor is not a model.** A model proposes; governed code decides. Giving a
> model a tool is not giving it authority.

## Run order and timing
| Step | Command | Time | The beat to land |
|---|---|---|---|
| 1 | `uv run sovereign-agent demo store --mode simulated` | ~1 s | The company only accepts work when reality matches the claim. (In the book: break the DB → verification refuses, exit 1.) |
| 2 | `uv run python demo_tool_calling.py` | ~20–40 s | A **real** local model **calls a tool** it was handed. Then: cost comes from the ledger, and 9999 units is **refused**. |
| 3 | `uv run python demo_full_governance.py` | ~30–60 s | The model's proposal flows through the **whole** loop to a committed, verified, **accepted** outcome. Money moved. |

## Talking points
- **Step 2, the tool call:** "Nobody told it to call the tool in code — it read
  the tool's description and decided to. That's the agentic part." Then: "and yet
  the *company* doesn't trust the number it gave back."
- **Step 2, the refusal:** ask the room "what if the model had said 9999?" — then
  run it and show the refusal. Bounded authority, in code, not vibes.
- **Step 3:** "This is the same governance loop as Step 1, but the actor is now a
  real model instead of a script. The governance didn't change. That's the
  design: intelligence is swappable; the guarantees are not."
- The number the model proposes may vary run to run — **feature, not bug**: it's
  a real model. Governance copes with whatever it says.

## If a laptop fights back
- `Python 3.14+ not found` → python.org or `pyenv install 3.14.3`. (Hard
  requirement of sovereign-agent 1.0.0.)
- `Connection refused` on 11434 → Ollama app isn't running (`ollama serve`).
- Slow first run → model loading into RAM; warm it: `printf '' | ollama run qwen3:latest`.
- Low RAM → stay on the default small model; do **not** use the 35B option.
- Stronger actor on a big machine: `SOVEREIGN_DEMO_MODEL=qwen3.6:35b uv run python demo_full_governance.py`.

## What's real here (in case someone asks / doubts)
- The model runs locally via Ollama. No API key, no network call offsite.
- The tool is a genuine ZeoCore `@capability` with a typed schema and a declared
  READ effect (`store_tool.py`).
- The frameworks are the **published PyPI packages**, installed into a venv —
  not the source repos, not editable installs. This is real end-user usage.
