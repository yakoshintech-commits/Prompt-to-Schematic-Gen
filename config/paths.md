# Config Plan - v1

```yaml
# pcbschemagen_dir: external, read-only dependency, not part of this project's own git
# history (still gitignored - see .gitignore) but physically nested inside this
# project's own directory per the "nothing lives outside root-project" decision
# (2026-09-18) - moved here from /scratch/k2983/PCBSchemaGen_v2.
pcbschemagen_dir: /scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2

# schgen_dir: this project's own actively-developed clone of SchGen (its own git
# history, gitignored from this project's repo - see .gitignore). Real hardening
# and verify-and-retry work happens here.
schgen_dir: /scratch/k2983/root-project/pcb-schematic-gen/SchGen

# schgen_upstream_reference_dir: pristine, untouched upstream checkout, kept only
# for occasional syncing against upstream SchGen. Never edited directly. Moved here
# (2026-09-18) from /scratch/k2983/SchGen - its .venv was pulled out into
# schgen_venv_dir below, a shared, top-level location, since the venv living inside
# THIS specific clone is exactly what caused the PROJECT_PATH bug documented below.
schgen_upstream_reference_dir: /scratch/k2983/root-project/pcb-schematic-gen/SchGen-upstream-reference

# schgen_venv_dir: the Python venv used to run SchGen (either clone - always pass
# --model_path / cd into the clone you actually want; PROJECT_PATH still governs
# which clone's `modules/*` gets imported, see the section below). Shared rather
# than duplicated per clone to avoid ~10GB of duplicated PyTorch/CUDA/flash-attn
# install. Moved here (2026-09-18) from inside schgen_upstream_reference_dir.
schgen_venv_dir: /scratch/k2983/root-project/pcb-schematic-gen/.venv

# models_dir: local model weights (base gpt-oss-20b + SchGen's LoRA adapter).
# Moved here (2026-09-18) from /scratch/k2983/models.
models_dir: /scratch/k2983/root-project/pcb-schematic-gen/models

# hf_cache_dir: HuggingFace download cache (HF_HOME). Moved here (2026-09-18)
# from /scratch/k2983/hf_cache; the venv's activate script sets HF_HOME to this
# path automatically.
hf_cache_dir: /scratch/k2983/root-project/pcb-schematic-gen/hf_cache

# This project's own code.
layer1_dir: layer1/
skills_dir: skills/

# Data. The durable copy lives off the university machine - see README.md for
# the session start and end sync commands.
# EDIT these two to your actual Hugging Face dataset repo and scratch path.
hf_dataset_repo: microsoft/SchGen_dataset
local_data_dir: /scratch/k2983/root-project/pcb-schematic-gen/SchGen_dataset

# Commands
test_command: python layer1/test_pipeline.py
verify_context: scripts/verify_context.sh
reports_dir: reports/
evidence_dir: evidence/
```

This is the portability layer. If infrastructure moves, for example a different university system or a new checkout location, one file changes here, not every reference scattered across Work Items and skills.

## Critical: running SchGen - the PROJECT_PATH trap

The Python venv for SchGen used to live at `schgen_upstream_reference_dir/.venv` (physically inside the pristine reference clone, a pre-existing setup decision, not this project's choice) - this was the actual root cause of a multi-hour debugging chain (2026-09-18): its `bin/activate` script hardcoded `export PROJECT_PATH=<the pristine clone>`, and `generate.py` does `sys.path.append(os.environ["PROJECT_PATH"])` to make its own `modules` package importable, so **every SchGen run silently imported `modules/*` from the pristine, unfixed clone, not the actively-developed one** - meaning the eager-attention fix in `llm_interface.py` was never actually active, and `flash_attention_2`'s known garbled-output bug kept firing regardless of which directory the entry script itself was run from. Full diagnostic trail in `skills/schgen-integration/SKILL.md`.

**Fixed properly, not just worked around** (2026-09-18): the venv was pulled out of the pristine clone entirely and now lives at the shared, top-level `schgen_venv_dir` above. Its `activate` script now defaults `PROJECT_PATH` to `schgen_dir` (the editable, actively-developed clone) correctly. A bare `source .venv/bin/activate` is now correct by default:
```bash
source /scratch/k2983/root-project/pcb-schematic-gen/.venv/bin/activate
cd /scratch/k2983/root-project/pcb-schematic-gen/SchGen
python3 schematic_generation/generate.py ...
```
If you ever need to run the *pristine* clone specifically (e.g. to diff against upstream), override explicitly: `export PROJECT_PATH=<schgen_upstream_reference_dir>` after activating, and `cd` there instead.
