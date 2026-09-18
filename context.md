# System Context - v3

<!-- BASELINE HASHES - verified at sprint start
global.md             v1  sha256:db727cad07960cffd3f0e9c2499d19690729ddcad7d9d7f3af2a0d3ca7ff27eb
instructions.md       v2  sha256:0f353bc905e21d0682a6841a10108e22424a2ac14c2178050b15c26620ab49fb
conventions.md        v2  sha256:f35a8cb17e17e9d34d2363d866fcb465d132bd8565df93c7164cf13ad1868b30
skills/manifest.yaml  v1  sha256:5aa7e12f041955d5701ee5d4e28b88bcdafe91671d1f67ca1d4098526b382d64
-->

## Charter - v2 (Sponsor decision, 2026-09-17)

- Build Layer 1: vague prompt to verified, KG-grounded architecture candidates, feeding into a hardened SchGen for final schematic generation.
- SchGen hardening is now in scope: this project's own clone (schgen_dir) already has 10 real bugs fixed and a working verify-and-retry loop (build + ERC check + feed real error back on failure), proven to self-correct across 2 error types on one case. Generalizing across more prompts is in progress.
- Success criteria: Layer 1 end-to-end run on three or more varied prompts, zero unflagged hallucinations, verify-and-retry generalizes beyond its first proven case, no interference with other concurrently running GPU processes, findings captured as skills.
- Constraints: no new paid API for generation, PCBSchemaGen_v2 is read-only, GPU is shared, university compute is time-limited.

## Standards - v2 (Sponsor decision, 2026-09-17)

- Forbidden paths: the pristine schgen_upstream_reference_dir checkout (read-only, sync-only), PCBSchemaGen_v2 checkout except an additive wrapper, and the baseline docs.
- Git: every commit gets its own task branch first; merge to main/master only at a clear completion point or on Sponsor say.
- Definition of Done includes writing non-obvious findings into skills/.
- Review cadence: portfolio default. Skip if the last two sprints were clean. Tighten on any rework or hash failure.

## Model Assignment - v2 (revised 2026-09-18 - corrects a real drift between this table and actual practice, not a new decision)

| Task type | Primary | Fallback |
|---|---|---|
| Reasoning, planning, orchestration, Sprint Workflow execution | Claude Code | none yet |
| Code execution (generation/completion of a scoped code piece, dispatched from within a Claude Code sprint) | Ollama (llama3.1:8b) | none yet |

**v1 said `deepseek-coder:33b` (the portfolio's original reference default, see `models/wrappers/ollama-deepseek.md`) - this project actually settled on `llama3.1:8b` on 2026-09-17/18, for Layer 1's constrained candidate generation, and this table was never updated to match. Real reason for the deviation, not a preference: a head-to-head test on this exact task (strict-JSON generation constrained to a small allowed-component vocabulary) showed `deepseek-coder:33b` inventing a fabricated part_id (`"IC1"`) not present in the allowed vocabulary, despite an explicit rule forbidding it; `llama3.1:8b` did not. Full comparison evidence in `skills/local-llm-setup/SKILL.md`. `deepseek-coder:33b` remains installed and available - this is a project-specific, evidence-based choice, not a portfolio-wide replacement of the default.**

Not a same-task-type Fallback pair. Ollama's model has no autonomous file/shell/git access and
does not run the Sprint Workflow itself - Claude Code dispatches scoped code-generation work to
it, then integrates, verifies, and commits the result itself. See
models/wrappers/ollama-deepseek.md for the full Role Brief (portfolio-wide, describes the *role*
- still accurate regardless of which specific model fills it) and models/capability.md for the
portfolio-wide matrix. GPU is shared with SchGen - check headroom before every invocation.

## SOP Register - v1 (unchanged since setup)

Empty. No vetted SOPs yet. See skills/manifest.yaml.

## Lessons - v3 (last updated: 2026-09-18)

- Real, substantial prior work (SchGen debugging: 10 bug fixes, a working verify-and-retry loop) existed only as uncommitted changes on shared university infrastructure, with no version control safety net. It survived by luck. Commit real work immediately, even mid-investigation, before it's "done" - don't wait for a clean stopping point.
- A separate, unrelated project (`prompt_schematic`, pure CI/hook scaffolding, no real content) was deleted and its GitHub history force-pushed over in the same general cleanup effort that could have touched the real SchGen work above. Near-miss: always verify what's actually real/valuable versus placeholder before any bulk cleanup or consolidation, per-item, not by directory.
- The verify-and-retry loop's earlier proven self-correction (a syntax error, a semantic wiring error) does not generalize to exact-string near-misses: confirmed across 3 attempts, with the correct symbol name explicitly delivered as feedback every time in a proper multi-turn structure, that a greedy-decoding (do_sample=False) model can still repeat the identical wrong guess verbatim - it has a strong enough prior for a plausible-but-wrong name that textual correction alone doesn't override it. A deterministic, narrowly-scoped, loudly-logged fuzzy-match auto-correction (kicad_add_symbol.py, 0.85+ similarity, single unambiguous match only) was built and confirmed working, then reverted same day: once two more hallucination classes turned up alongside it (pin-count mismatch, dropped symbol placement), keeping a stopgap for only the first-discovered one would have been inconsistent - all three get the same systemic fix instead. This is directly relevant to Layer 1's design: validate_facts.py's hard hallucination filter must catch unresolvable component/pin references before generation, not rely on the generative model to self-correct them after the fact, and not on ad hoc per-symptom patches either - retry-with-feedback is not a substitute for grounding.

## Loaded this sprint

- Role Brief: claude-code.md
- Work Item: T001
- SOP: none yet

---

**Before the first sprint runs**, fill in the PENDING hashes above. See README.md for the exact command.
