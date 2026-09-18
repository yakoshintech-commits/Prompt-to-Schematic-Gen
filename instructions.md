# Project Charter - v2

## What we're building

A grounded, hallucination-resistant pipeline for generating PCB schematics from natural-language requests, built on top of a fine-tuned schematic-generation model, SchGen, which this project now actively hardens rather than treating as an untouchable black box.

The pipeline has two layers, plus the SchGen hardening work that sits underneath both.

**SchGen hardening** (real work already done before this charter version, continuing): SchGen shipped with real bugs blocking basic use on this environment - a syntax error, a hardcoded unreachable Microsoft-internal Azure endpoint, a dual-model VRAM overflow, raw reasoning text leaking into JSON parsing, a flash_attention_2 bug producing garbled output, oversized prompts overflowing memory, unreliable JSON needing a repair pass, a code-extraction bug, and a missing data file. All fixed. A verify-and-retry loop was then built around SchGen's generation step: build the KiCad project, run its Electrical Rules Check, and on failure feed the real error back to the model as a new turn. Validated live: the model self-corrected a syntax error and a semantic wiring error purely from real error text, passing on attempt 3. This work happens on this project's own clone of SchGen, kept at the path named `schgen_dir` in `config/paths.md`.

**Layer 1** (new, being built under this system): takes a vague user prompt, proposes several architecturally distinct candidate designs grounded in a real component knowledge graph, verifies each candidate deterministically before a user ever sees it, and lets the user pick one, either manually or via configurable weighted scoring.

**Translation and generation** (the hardened SchGen from above): the chosen candidate is translated into a natural-language request written in SchGen's exact input style, then SchGen generates the actual KiCad schematic.

## Why

Free-form LLM generation of circuit designs hallucinates components and pin connections that do not exist. Layer 1 exists to catch this before a user ever sees a candidate, by constraining generation to a real, verified knowledge graph and running a deterministic verifier against every candidate before it is shown.

## Success criteria

- Layer 1 runs end-to-end on three or more varied vague prompts and returns ranked, verified candidates.
- Zero unflagged hallucinated components or pins reach the user. Every candidate's verification_status is set correctly before it is shown.
- The verify-and-retry loop's self-correction capability, already proven on one case, is confirmed to generalize across varied prompts, not specific to the case it was first proven on.
- The pipeline never interferes with or interrupts any other concurrently running process on the shared GPU.
- Every non-obvious finding from investigating dependency internals, such as PCBSchemaGen_v2's real verifier contract, SchGen's real bugs and fixes, or the knowledge graph schema, is captured in a skill under skills/, not only shown once in a session and lost.

## Constraints

- No new paid API dependency for Layer 1's generation step. Use a local model.
- PCBSchemaGen_v2's own code is a read-only dependency. Only a documented, minimal wrapper may be added on top of it, to load its larger component knowledge graph, without modifying its existing files.
- SchGen is developed via this project's own clone at `schgen_dir` (config/paths.md), not treated as read-only. A separate pristine upstream reference copy is kept at `schgen_upstream_reference_dir` for occasional syncing only - never edited directly.
- The GPU is shared with other processes at times. Never assume it is idle. Check available VRAM before running any local model inference, and default to CPU-only if in doubt.
- University compute access is time-limited per session. See conventions.md for the current window and config/paths.md for where the durable copy of any dataset lives, since local storage on the university system should be treated as ephemeral.

## References

See config/paths.md for the mapping from logical names to real paths and commands.
See conventions.md for engineering standards specific to this project.
Cross-project standards live in global.md at the portfolio root, not here.
