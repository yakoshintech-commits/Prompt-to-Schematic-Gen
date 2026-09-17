# Project Charter - v1

## What we're building

A grounded, hallucination-resistant pipeline for generating PCB schematics from natural-language requests, layered on top of an existing fine-tuned schematic-generation model, SchGen.

The pipeline has two layers.

**Layer 1** (new, being built under this system): takes a vague user prompt, proposes several architecturally distinct candidate designs grounded in a real component knowledge graph, verifies each candidate deterministically before a user ever sees it, and lets the user pick one, either manually or via configurable weighted scoring.

**Translation and generation** (existing, not modified by this project, only handed off to): the chosen candidate is translated into a natural-language request written in SchGen's exact input style, then SchGen generates the actual KiCad schematic.

## Why

Free-form LLM generation of circuit designs hallucinates components and pin connections that do not exist. Layer 1 exists to catch this before a user ever sees a candidate, by constraining generation to a real, verified knowledge graph and running a deterministic verifier against every candidate before it is shown.

## Success criteria

- Layer 1 runs end-to-end on three or more varied vague prompts and returns ranked, verified candidates.
- Zero unflagged hallucinated components or pins reach the user. Every candidate's verification_status is set correctly before it is shown.
- The pipeline never interferes with or interrupts a concurrently running SchGen process.
- Every non-obvious finding from investigating dependency internals, such as PCBSchemaGen_v2's real verifier contract or its knowledge graph schema, is captured in a skill under skills/, not only shown once in a session and lost.

## Constraints

- No new paid API dependency for Layer 1's generation step. Use a local model.
- SchGen's own codebase and PCBSchemaGen_v2's own code are read-only dependencies. Only a documented, minimal wrapper may be added on top of PCBSchemaGen_v2, to load its larger component knowledge graph, without modifying its existing files.
- The GPU is shared with SchGen at times. Never assume it is idle. Check available VRAM before running any local model inference, and default to CPU-only if in doubt.
- University compute access is time-limited per session. See conventions.md for the current window and config/paths.md for where the durable copy of any dataset lives, since local storage on the university system should be treated as ephemeral.

## References

See config/paths.md for the mapping from logical names to real paths and commands.
See conventions.md for engineering standards specific to this project.
Cross-project standards live in global.md at the portfolio root, not here.
