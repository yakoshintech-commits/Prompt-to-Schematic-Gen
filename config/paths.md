# Config Plan - v1

```yaml
# pcbschemagen_dir: external, read-only dependency, not part of this project's own git history.
pcbschemagen_dir: /scratch/k2983/PCBSchemaGen_v2

# schgen_dir: this project's own actively-developed clone of SchGen (its own git
# history, gitignored from this project's repo - see .gitignore). Real hardening
# and verify-and-retry work happens here.
schgen_dir: /scratch/k2983/root-project/pcb-schematic-gen/SchGen

# schgen_upstream_reference_dir: pristine, untouched upstream checkout, kept only
# for occasional syncing against upstream SchGen. Never edited directly.
schgen_upstream_reference_dir: /scratch/k2983/SchGen

# This project's own code.
layer1_dir: layer1/
skills_dir: skills/

# Data. The durable copy lives off the university machine - see README.md for
# the session start and end sync commands.
# EDIT these two to your actual Hugging Face dataset repo and scratch path.
hf_dataset_repo: microsoft/SchGen_dataset
local_data_dir: /scratch/k2983/SchGen_dataset

# Commands
test_command: python layer1/test_pipeline.py
verify_context: scripts/verify_context.sh
reports_dir: reports/
evidence_dir: evidence/
```

This is the portability layer. If infrastructure moves, for example a different university system or a new checkout location, one file changes here, not every reference scattered across Work Items and skills.

## Critical: running SchGen - the PROJECT_PATH trap

The Python venv for SchGen lives at `schgen_upstream_reference_dir/.venv` (physically inside the pristine reference clone, a pre-existing setup decision, not this project's choice). Its `bin/activate` script hardcodes `export PROJECT_PATH=<schgen_upstream_reference_dir>`, and `generate.py` does `sys.path.append(os.environ["PROJECT_PATH"])` to make its own `modules` package importable - meaning **every SchGen run silently imports `modules/*` from the pristine, unfixed clone, not the actively-developed one, unless PROJECT_PATH is explicitly overridden after activating**.

Confirmed empirically (2026-09-18): this caused every real SchGen invocation that afternoon to silently run on unfixed code (the eager-attention fix in `llm_interface.py` was never actually active - `flash_attention_2`'s known garbled-output bug fired every time), even though the entry script itself was correctly run from `schgen_dir`. Running the exact same prompt with `PROJECT_PATH` corrected produced a clean, correct result immediately - see `skills/schgen-integration/SKILL.md`.

**Always run SchGen like this**, never bare `source .venv/bin/activate` alone:
```bash
source /scratch/k2983/SchGen/.venv/bin/activate
export PROJECT_PATH=/scratch/k2983/root-project/pcb-schematic-gen/SchGen   # overrides the venv's own wrong default
cd /scratch/k2983/root-project/pcb-schematic-gen/SchGen
python3 schematic_generation/generate.py ...
```
(The venv's activate script has also been corrected directly to default to the right path - see SKILL.md - but the explicit `export` above is the belt-and-suspenders version and costs nothing.)
