# KG Expansion Charter

## Goal
Grow the curated component knowledge graph from 243 parts toward meaningful
coverage of the 20,308-entry candidate pool (`PCBSchemaGen_v2/kg/kg_candidate_pool.json`),
at the same curation rigor already proven on `Antenna`/`Stepper_Motor_bipolar`
and this session's batches — not a bulk, unverified merge. This is standing,
ongoing work, not a side task: production-grade vague-prompt-to-schematic
coverage is the actual deliverable.

## Why batches, not a bulk merge (evidence, not caution for its own sake)
Four separate times this project has measured that changing the candidate
pool a generation model chooses from — even with individually-correct
additions — can regress accuracy on the existing, already-working set
(T027, T032, T033, and the reverted SchGen diversity-fix detour). Pool size
and composition are themselves a measured risk factor, independent of data
quality. So: small batches, hand-verified, each followed by a full
regression check before the next batch starts.

## Per-batch process
1. Pull candidates from `kg_candidate_pool.json`, prioritized for real-world
   usefulness and genuine gaps in current coverage (check the live KG first —
   don't duplicate what's already curated).
2. Prefer clean, unambiguously-named real pins. Deliberately defer
   all-unnamed-pin (`~`) parts until there's headroom to test them
   specifically — that's the exact failure class (pin-naming hallucination)
   this session already spent real effort fixing; don't reintroduce more of
   it while that fix is still being validated.
3. Hand-assign `pin_roles` only where unambiguous, matching established
   convention exactly (`i2c_sda`/`i2c_scl`, `supply_vdd`/`supply_gnd`,
   `usb_vbus`/`usb_dp`/`usb_dm`/`usb_shield`, `logic_in`/`logic_out`, etc. —
   check `phase2_checks.py`'s `_GENERIC_ROLE_FAMILIES` before inventing a new
   family, so new roles actually participate in existing checks instead of
   silently falling outside them).
4. Stage drafts (not live KG) until a batch is complete, then merge.
5. Live-test each new part in isolation via real Layer 1 generation before
   trusting it structurally resolves.
6. Run a full-population regression validation after merging a batch,
   before starting the next one. Compare the clean, matched diff — not the
   raw pass/fail count — the same discipline that caught every real
   regression this session (reused/stale baselines corrupt comparisons;
   isolated rechecks distinguish real defects from this pipeline's own
   measured nondeterminism).

## Resourcing rule
- CPU-only work (candidate selection, hand curation, drafting) has no
  resource conflict with anything GPU-bound — runs continuously, in
  parallel, regardless of what else is running.
- GPU-bound work (live-testing a new part via Layer 1/Ollama, any full
  validation run via SchGen's local model) is sequenced, never run
  concurrently with another GPU-bound job on this machine. Check
  `nvidia-smi` headroom before starting one.
- Never touch the live KG (`kg_open_schematics.json`) or pipeline config
  files while a validation run that depends on them is in progress.

## Batch log
| Batch | Parts | Status | Notes |
|---|---|---|---|
| 1 | `USB_A`, `USB_B`, `Conn_01x02`, `Conn_01x03`, `Conn_01x04`, `Transformer_1P_1S`, `Transformer_1P_2S`, `SW_DPST` | drafted, staged (not merged) | Connectors/passives, clean named pins, confirmed non-redundant vs. live KG |
| 2 | `BME280`, `SHT31-DIS`, `LM35-D`, `PCF8574`, `DS1307+`, `PCA9685PW` | drafted, staged (not merged) | Common ICs (env. sensors, I2C expander, RTC, PWM driver), `i2c_sda`/`i2c_scl` roles confirmed against existing convention |
| 3+ | TBD | pending | Continue in background while GPU is busy with validation |

## Open items
- Merge batches 1-2 into the live KG once the current full-pipeline
  validation (pin-number-preference fix) completes and the GPU is free.
- Live-test each of the 14 drafted parts individually before merging.
- Run a full regression validation after the merge.
- Continue drafting further batches in parallel (CPU-only), prioritizing:
  genuine gaps in current coverage, parts that could close one of Layer 1's
  6 still-open companion-omission failures (the highest-leverage kind of
  addition - closes a known gap, not just adds breadth), then common
  real-world parts by category.
