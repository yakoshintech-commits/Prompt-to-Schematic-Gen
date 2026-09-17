# pcb-schematic-gen - Onboarding

This file is Tier 4. Read it once, when setting up, or when a new person joins. Not loaded into any Developer session's context bundle.

## One-time setup, in order

1. Edit config/paths.md. Set schgen_dir and pcbschemagen_dir to your real local checkout paths. Set hf_dataset_repo and local_data_dir to your real values.

2. Compute the real baseline hashes and paste them into context.md, replacing every PENDING:
   ```
   cd pcb-schematic-gen
   chmod +x scripts/verify_context.sh scripts/check_deferred.sh
   scripts/verify_context.sh --update
   ```
   Copy the printed sha256 values into context.md's hash block at the top of the file, one per baseline file.

3. Confirm it passes:
   ```
   scripts/verify_context.sh
   ```
   You should see: verify_context.sh: PASS.

4. Initialize git and wire up the pre-commit hook:
   ```
   git init
   cp .githooks/pre-commit .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   git add .
   git commit -m "chore(setup): initial project scaffold"
   ```

5. Tag the starting point, per the Rollback Protocol:
   ```
   git tag sprint-start-T001
   ```

## Running the first sprint

Follow PIPELINE.md section 15, the Sprint Workflow, exactly. Concretely, for T001:

1. Read tasks/T001-layer1-grounded-pipeline.md yourself first. Confirm the Inputs section's two external paths are correct in config/paths.md.
2. Assemble the context bundle for the Developer session: models/wrappers/claude-code.md, plus this project's context.md, handoff.md, and tasks/T001-layer1-grounded-pipeline.md. No SOP is named yet, so none is included.
3. Hand this bundle to Claude Code. Have it restate the work and plan before it starts executing, per step 7 of the Sprint Workflow. Approve or redirect before it proceeds.
4. Let it execute. It should update progress.md as it goes, log any mid-sprint correction as a Lesson in context.md, run the verification command from the Work Item at step 10a with real captured output into evidence/, then update handoff.md and sessions.md and commit.
5. After the sprint, run scripts/verify_context.sh yourself to confirm the hash check still passes, and read handoff.md to see what it reports.

## Data sync, given the ten-day university access window

Treat the university system as ephemeral compute only. At the start of each session:
```
huggingface-cli download <hf_dataset_repo from config/paths.md> --repo-type dataset --local-dir <local_data_dir from config/paths.md>
```
Before your access window ends:
```
huggingface-cli upload <hf_dataset_repo from config/paths.md> <local_data_dir from config/paths.md> --repo-type dataset
```

## GPU safety

SchGen may be running concurrently on the same GPU. Before running any local model inference for Layer 1, check headroom:
```
nvidia-smi
```
Confirm several gigabytes of free VRAM beyond what is already in use before proceeding. Default to CPU-only inference if in doubt. See skills/schgen-integration/SKILL.md, once T001 populates it, for the confirmed-safe pattern.

## After T001

Check deferred.md and run the Trigger Review ritual once the cadence in PIPELINE.md section 12 calls for it. scripts/check_deferred.sh gives a quick count to speed that up, but the Sponsor still reads deferred.md directly to judge whether any row's trigger has actually fired.
