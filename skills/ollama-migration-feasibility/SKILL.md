# T002: SchGen -> Ollama Migration Feasibility

## Purpose

Findings from investigating whether SchGen's fine-tuned model (gpt-oss-20b + LoRA adapter) can move to Ollama-served GGUF weights, per the Sponsor's goal of unifying local model serving. Backlog's own instruction: investigate feasibility before committing to a full Work Item spec. This is that investigation.

## Key facts (confirmed empirically, not assumed)

**Base model support is not the blocker - Ollama officially, natively supports gpt-oss-20b.** OpenAI partnered directly with Ollama for day-one support; has worked since Ollama v0.11.5+ (this cluster runs 0.34.1). Source: [ollama.com/library/gpt-oss:20b](https://ollama.com/library/gpt-oss:20b).

**The real blocker is merging SchGen's specific LoRA adapter shape - and a direct numeric test proves the naive approach is currently broken, not just risky.** SchGen's adapter (`adapter_config.json`) uses standard `target_modules` (`q_proj`/`k_proj`/`v_proj`/`o_proj` - low risk, well-trodden) PLUS `target_parameters` on 3 specific MoE expert layers (7/15/23's `gate_up_proj`/`down_proj` - the unusual, high-risk part). Real tensor shapes confirm the adapter's `lora_B` for the expert layers has shape `[5760, 256]`, where `256 = 8 (rank) x 32 (num_experts)` - a packed axis, exactly the kind of structure a real, recently-fixed Unsloth/PEFT ordering bug affects (see below) - though that specific bug doesn't apply here (no Unsloth involved, confirmed - see next fact).

**Ran the actual test, not just researched the risk (2026-09-18).** Loaded SchGen live (base + adapter, unmerged, the exact same loading path `generate.py` already uses), ran a fixed test prompt, captured the real output logits. Called PEFT's own `merge_and_unload()` (peft==0.17.0, the version already installed and presumably what trained this adapter - no cross-version mismatch). Ran the same prompt through the merged model. Compared outputs directly:

- PEFT itself warned during the merge: `Unsupported layer type '<class 'transformers.integrations.mxfp4.Mxfp4GptOssExperts'>' encountered, proceed at your own risk.` Even after the expert weights are dequantized to plain numbers (via the same code generate.py already uses for its own custom loading), the module's Python *class* is still tagged `Mxfp4GptOssExperts` - PEFT's merge logic doesn't recognize that class as one it knows how to handle, and merges anyway without a hard error.
- Real numeric result: **max absolute logit difference = 1.47, mean = 0.07**, against a live logit range of about 34 (roughly -16 to +18.5). This is far larger than bf16 rounding noise (~0.01-0.05 expected). Top-1 predicted token happened to still match for this one prompt (`' resistor'` both times) - a coincidence, not proof; a 1.47 gap is easily large enough to flip the answer on a closer call.
- Full log: `evidence/T002-merge-numeric-verification.log`.

**No Unsloth-vs-PEFT mismatch applies here - checked directly, not assumed.** `unsloth` is not installed in this project's venv, and `adapter_config.json` shows plain `peft_type: "LORA"` with no Unsloth-specific metadata (no `lora_B_layout` marker, which the recent Unsloth fix added). This adapter was almost certainly trained with plain HuggingFace PEFT, not Unsloth - so the specific cross-tool ordering bug researched earlier (fixed 2026-09-17 in `unslothai/unsloth-zoo`) is very likely not the cause of the discrepancy found here. The real cause is PEFT's own merge code not correctly handling this specific dequantized-but-still-MXFP4-classed module type - a different, SchGen-environment-specific problem, not the one from the news.

## Verdict (revised 2026-09-18, after deeper localization - the first verdict below was too strong)

**The merge math itself is correct; the "unsupported layer type" warning is a false positive; the output divergence is explained, not a demonstrated bug.** Follow-up investigation, in order:

1. Traced the "Unsupported layer type" warning to `LoraLayer.__init__`'s generic isinstance-based type detection (a shared code path also used by `target_modules`-style LoRA) - it fires before `ParamWrapper.__init__` immediately overrides `in_features`/`out_features` with correctly-computed values from the real parameter shape. Cosmetic noise, not evidence of a broken merge.
2. Confirmed `get_delta_weight()` (the function that computes the LoRA correction) is the exact same function used both for live, unmerged inference (via `_activate_lora`'s `register_parametrization`) and for `merge()` (`param.data += delta_weight`) - mathematically, these should be identical operations.
3. Directly compared the actual weight change after merge against the independently-computed expected delta for layer 7's `gate_up_proj`: max/mean absolute values matched exactly; only a small per-element residual (0.0032 against a 0.0486 max) remained, consistent with `bf16` rounding from subtracting two close numbers (a known precision trap), not a wrong computation.
4. **The real explanation for the original 1.47 max logit difference**: hooked the router module on all 3 target layers and compared actual expert-selection decisions between live and merged runs on the same prompt. Layer 7: identical. Layer 15: 2 of 14 token positions selected a genuinely different *set* of top experts. Layer 23: same expert set, harmless reordering only. A tiny numeric difference was enough to flip a discrete top-k routing decision for 2 tokens - an inherent sensitivity of MoE architectures to small perturbations near a decision boundary, not a demonstrated flaw in the merge itself. Full log: `evidence/T002-routing-check.log`.

**Practical implication**: some level of non-bit-identical output should be *expected* whenever this model's inference path changes at all (different merge, different kernel, different inference engine like llama.cpp/Ollama) - MoE routing sensitivity means this isn't unique to PEFT's merge and can't be fully eliminated by fixing the merge alone. The real open question for feasibility isn't "is the merge broken" (evidence says no) but "is this level of occasional routing drift acceptable for SchGen's use case" - worth testing with real SchGen prompts (not just one probe prompt) and comparing actual generated schematic code, not just raw logits, before deciding.

## Common mistakes to avoid

- Don't trust "the merge ran without crashing" or "the top predicted token still looks right" as evidence of correctness - both were true here, and the merge is still measurably wrong. Always compare raw output numbers against the live, unmerged baseline before trusting a merged model.
- Don't assume dequantizing a module's *weights* also changes how PEFT (or any tool) treats its *class* - the warning fired because the class was still `Mxfp4GptOssExperts` even after its parameters were replaced with plain dequantized values.

## Code references

- `evidence/T002-merge-numeric-verification.log` - the real test run and its output
- `models/SchGen-adapter/adapter_config.json` - the real adapter structure (target_modules + target_parameters)
- `SchGen/schematic_generation/generate.py` - the existing, working, hand-rolled MXFP4 dequant approach this test's loading code reused
