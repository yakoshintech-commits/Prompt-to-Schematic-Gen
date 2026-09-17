# System Context - v2

<!-- BASELINE HASHES - verified at sprint start
global.md             v1  sha256:db727cad07960cffd3f0e9c2499d19690729ddcad7d9d7f3af2a0d3ca7ff27eb
instructions.md       v1  sha256:4c5e54099e98b9baa11a97dde62616feb47442f3af142fc79952868bf0a8b654
conventions.md        v1  sha256:9029ae389d10dccb9efbbf7e48f55db36ebc92da40be50ced3b1f9bc2c398b91
skills/manifest.yaml  v1  sha256:5aa7e12f041955d5701ee5d4e28b88bcdafe91671d1f67ca1d4098526b382d64
-->

## Charter - v1 (unchanged since setup)

- Build Layer 1: vague prompt to verified, KG-grounded architecture candidates, feeding into existing SchGen for final schematic generation.
- Success criteria: end-to-end run on three or more varied prompts, zero unflagged hallucinations, no interference with concurrently running SchGen, findings captured as skills.
- Constraints: no new paid API for generation, SchGen and PCBSchemaGen_v2 are read-only, GPU is shared with SchGen, university compute is time-limited.

## Standards - v1 (unchanged since setup)

- Forbidden paths: SchGen checkout, PCBSchemaGen_v2 checkout except an additive wrapper, and the baseline docs.
- Definition of Done includes writing non-obvious findings into skills/.
- Review cadence: portfolio default. Skip if the last two sprints were clean. Tighten on any rework or hash failure.

## Model Assignment - v1 (added 2026-09-17, Sponsor decision)

| Task type | Primary | Fallback |
|---|---|---|
| Reasoning, planning, orchestration, Sprint Workflow execution | Claude Code | none yet |
| Code execution (generation/completion of a scoped code piece, dispatched from within a Claude Code sprint) | Ollama (deepseek-coder:33b) | none yet |

Not a same-task-type Fallback pair. Ollama's model has no autonomous file/shell/git access and
does not run the Sprint Workflow itself - Claude Code dispatches scoped code-generation work to
it, then integrates, verifies, and commits the result itself. See
models/wrappers/ollama-deepseek.md for the full Role Brief and models/capability.md for the
portfolio-wide matrix. GPU is shared with SchGen - check headroom before every invocation.

## SOP Register - v1 (unchanged since setup)

Empty. No vetted SOPs yet. See skills/manifest.yaml.

## Lessons - v1 (last updated: setup)

Empty. No sprints have run yet.

## Loaded this sprint

- Role Brief: claude-code.md
- Work Item: T001
- SOP: none yet

---

**Before the first sprint runs**, fill in the PENDING hashes above. See README.md for the exact command.
