# T013: Comprehensive Layer1 -> SchGen breadth/depth test

Full-coverage test: every single row in the SchGen-compatible KG (133
components), not a curated sample.

## Final results (2026-09-22)

- **Stage 1 (Layer 1, full breadth, all 133 rows):** 103 passed, 30
  failed_checks, 0 exceptions. Results: `t013_full_layer1_results.json`.
- **Stage 2 (SchGen/PyTorch, full depth on all 103 passing candidates):**
  **103/103 processed. 76/103 = 73.8% reached 0 ERC errors.** Results:
  `t013_full_schgen_results.json`.
  - 64 passed on the first attempt, 10 needed a retry, 2 needed all 3
    attempts, 27 exhausted all 3 attempts without a clean ERC pass.
  - Failed part IDs: 1N4148WS, 1N5819WS, 74HC04, 74HC14, 74LS08, 74LS32,
    ACS711xEXLT-15AB, ADS1115IDGS, AP63203WU, ATmega32A-P, ATtiny13A-P,
    BAW75, C, DRV5055A2xDBZxQ1, ESP32-S3-MINI-1U, L, LTV-817, MCP2562-E-MF,
    MPU-6000, NXE1S0303MC, S102S01, SN65HVD230, SN74LVC2T45DCUR, SW_SPDT,
    TPS54302, TPS60401DBV, W25Q128JVS.

## Overall pipeline yield across all 133 KG rows

103/133 (77%) pass Layer 1's grounding check, and of those 76/103 (74%)
reach a clean SchGen schematic - an overall ~57% (76/133) full-pipeline
success rate across the entire real KG, unfiltered.

## What it took to actually finish this run

The SchGen/PyTorch stage took ~2.5 days of real wall-clock time, not
because generation itself is slow (each candidate takes 5-30 minutes), but
because of a genuinely tricky, well-diagnosed infrastructure problem on
this shared machine: `systemd-oomd` (a userspace OOM killer distinct from
the kernel's) is configured to kill this whole user session
(`user@997413182.service`) if aggregate memory *pressure* - not raw
availability - exceeds 50% for 20 sustained seconds. Loading a ~14GB model
was enough to trip this, repeatedly, for ~30 consecutive attempts across
every time of day, completely independent of GPU/RAM headroom (confirmed
via live PSI tracing, cgroup inspection, and testing with a genuinely idle
machine - see evidence/T013-full-schgen-batch.log for the full
investigation). The actual unblock: closing a 26-process Chrome session
that was sharing the same monitored cgroup dropped the baseline pressure
enough for the load to succeed, and it then ran the remaining ~37
candidates to completion without further intervention.

Root-cause fix for next time (needs root, which this session did not
have): `ManagedOOMMemoryPressure=none` (or a higher
`ManagedOOMMemoryPressureLimit`) via a systemd drop-in on
`user@997413182.service`.

## To resume (if extending this test later)

```
source /scratch/k2983/root-project/pcb-schematic-gen/.venv/bin/activate
python3 t013_full_schgen_batch_gpuaware.py 2>&1 | tee -a ../evidence/T013-full-schgen-batch.log
```

It's idempotent - reads `t013_full_schgen_results.json` first and only
processes candidates not already in it. Requires `nvidia-smi` GPU memory
used to be under 300MB before it will attempt a model load.
