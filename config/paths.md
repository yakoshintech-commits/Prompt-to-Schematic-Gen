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
