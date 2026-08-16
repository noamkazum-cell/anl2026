# Agent drafts (not the final submission)

The **final uploaded agent** is at the repo root:

| File | Role |
|------|------|
| `../agent360_FINAL.py` | Source of the final submission (V4.6 label = restored V4.2 logic) |
| `../submitted_v4.zip` | Zip that was uploaded (`agent360.py` + `requirements.txt`) |
| `../agent360_submit_v4.py` | Tiny back-compat alias → `agent360_FINAL` |

## What lives here

| File | What it is |
|------|------------|
| `agent360.py` | Early modular base (`Agent360Base`) |
| `agent360_v2.py` / `agent360_v3.py` | Dev versions before the self-contained submit |
| `agent360_full.py` / `agent360_reverse.py` | Ablation / reverse-psychology experiments |
| `agent360_submit.py` + `submitted.zip` | **V3** legacy submission (rank ~28) |
| `agent360_submit_v42.py` + `submitted_v42.zip` | Frozen V4.2 snapshot for A/B |
| `agent360_submit_v45.py` | V4.5 experiment (stall-accept; rejected) |
| `agent360_v4.py` / `agent360_v4_2.py` / `agent360_v4_3.py` | Thin aliases / archived V4.3 |
| `opponent_classifier.py` / `persona_schedules.py` | Early modular helpers (inlined into final) |
