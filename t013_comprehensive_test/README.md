# T013: Comprehensive Layer1 -> SchGen breadth/depth test

Full-coverage test: every single row in the SchGen-compatible KG (133
components), not a curated sample.

## Status (as of 2026-09-20)

- **Stage 1 (Layer 1, full breadth, all 133 rows):** DONE. 103 passed, 30
  failed_checks, 0 exceptions. Results: `t013_full_layer1_results.json`.
- **Stage 2 (SchGen/PyTorch, full depth on all 103 passing candidates):**
  IN PROGRESS. 66/103 done (48/66 = 72.7% ERC-clean). Results:
  `t013_full_schgen_results.json`. Blocked by a shared-GPU 32GB single-card
  ceiling - our own process alone peaks near ~31GB, so it needs the GPU to
  be essentially idle to run at all. See evidence/T013-full-schgen-batch.log
  for the full run history, including a ~13.6h wait for another user's job
  to finish, and a still-unexplained pattern of instant kills even on a
  fully idle machine that never got fully diagnosed.

## To resume

```
source /scratch/k2983/root-project/pcb-schematic-gen/.venv/bin/activate
python3 t013_full_schgen_batch_gpuaware.py 2>&1 | tee -a ../evidence/T013-full-schgen-batch.log
```

It's idempotent - reads `t013_full_schgen_results.json` first and only
processes candidates not already in it. Requires `nvidia-smi` GPU memory
used to be under 300MB before it will attempt a model load (see the
comments in the script for why).
