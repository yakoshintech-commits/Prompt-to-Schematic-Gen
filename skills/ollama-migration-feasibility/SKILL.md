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

## Full end-to-end success (2026-09-18) - real, working prototype built and verified

Went all the way: merged the real adapter, converted to GGUF, served via Ollama, ran a real SchGen request through the exact same prompt-construction path `generate.py` uses (real symbol selection + `prepare_context()`), and built + ERC-checked the result. **0 ERC errors, real `.kicad_sch` file, entirely through Ollama.** Evidence: `evidence/T002-ollama-comparison.log`, `evidence/T002-ollama-gguf-response.txt`, `SchGen/t002_ollama_test/`.

Key technical points, in order, each one a real thing that had to be figured out empirically, not assumed:

1. **The important realization that reframed the whole investigation**: `generate.py` already calls `PeftModel.from_pretrained(...).merge_and_unload()` before every real generation (line 254). There is no "live, unmerged" code path in actual use - every verified-working SchGen result all session already ran on the merged model. The earlier live-vs-merged numeric comparisons were still useful (they explained *why* small divergences happen, via MoE routing sensitivity), but the real relevant comparison for feasibility was always "does GGUF/Ollama reproduce this already-trusted merged model's behavior," not "is merging itself safe."
2. **`save_pretrained()` can't be trusted for a partially-quantized model** - an untouched (still-MXFP4) expert layer doesn't even register `gate_up_proj`/`down_proj` as a normal PyTorch parameter or buffer (only the bias terms are registered), so the standard HF save path has no reliable way to round-trip it. Fixed by writing the checkpoint directly at the safetensors level: copy the original shards through untouched, surgically replace only the 6 tensors (3 layers x 2 projections) that actually changed.
3. **`llama.cpp`'s gpt-oss converter (`conversion/gpt_oss.py`) has a real, documented fallback for exactly this mixed situation** - tensors named with `_blocks`/`_scales` get read as native MXFP4-packed; any expert tensor without those suffixes gets treated as a plain dense weight (with a "not in MXFP4, performance may be degraded" warning, not an error). This is precisely the shape a partially-merged model has - not a workaround, a supported path.
4. **Got the tensor orientation wrong on the first attempt, caught immediately by a real error, not silently** - guessed that the converter wanted the "raw," pre-generate.py-transpose orientation and undid the in-memory `.transpose(1, 2)` before saving. Ollama's own error (`expected 2880,2880,32 got 5760,1440,32,1`) proved that guess backwards - the converter actually wants the tensor in generate.py's own *consumption* orientation (the transpose already applied), not the raw dequant orientation. Fixed by removing the undo step; conversion succeeded immediately after.
5. **Ollama correctly recognized the mixed-precision result** - `ollama ps` reports `"quantization_level":"MXFP4_MOE"` for the loaded model, confirming the untouched 21 layers stayed in their compact native format rather than the whole model silently ballooning to all-dense bf16.

**Verdict: T002 is feasible, and a real working prototype now exists.** The GGUF/Ollama model was tested with `--outtype bf16` for the merged layers specifically (not yet quantized down further, e.g. Q4_K_M, which would need its own correctness check before being trusted). But the hard technical risk (can SchGen's specific adapter shape actually make it through merge -> GGUF -> Ollama and still work) is resolved: yes, confirmed by real, ERC-clean, generated schematics across multiple varied prompts (see below), not a single lucky result.

## Broader validation + a real retry loop for the Ollama path (2026-09-18, same day)

Ran 2 more varied prompts (a 3.3V AP2112K linear regulator, a simple LED indicator) through the exact same rigorous method - real symbol selection, real `prepare_context()`, real KiCad build, real ERC check:

- **LED indicator**: passed cleanly, 0 ERC errors, first try.
- **AP2112K regulator**: failed the build step - the model asked for symbol `AP2112K`, but the real KiCad library only has voltage-suffixed variants (`AP2112K-3.3`, `AP2112K-2.6`, `AP2112K-2.5`). This is the exact same symbol-name near-miss hallucination class already documented in `backlog.md`'s T001 findings row - a pre-existing SchGen limitation, not something introduced by the merge/GGUF/Ollama pipeline.

Built `SchGen/schematic_generation/verify_and_retry_ollama.py` - a direct port of `verify_and_retry.py`'s proven generate -> build -> ERC -> feed real error back -> retry loop, but generating via Ollama's `/api/chat` instead of shelling out to `generate.py`'s local PyTorch model (symbol selection still runs locally - it's a generic task unrelated to which backend serves the merged model). Confirmed Ollama's chat API already returns clean, harmony-channel-stripped content directly (no `<|channel|>final<|message|>` wrapper to extract, unlike the raw HF `tokenizer.batch_decode` output `generate.py` has to parse).

Ran the retry loop on the exact regulator prompt that had just failed: **attempt 1 failed identically** (same `AP2112K` vs `AP2112K-3.3` mismatch), the real error (including the "Did you mean: [...]" hint) got fed back using the same proven multi-turn structure (previous response replayed as an assistant turn, error as a genuine user reply), and **attempt 2 corrected itself and passed with 0 ERC errors**. Full log: `evidence/T002-retry-loop-regulator.log`.

**Result across all real testing this session: 3/3 prompts reach a clean ERC pass** (USB_B connector and LED indicator directly; the regulator via one retry) - the same reliability shape already proven for the PyTorch-based pipeline, now demonstrated for the Ollama-served merged model too.

## Code references (end-to-end prototype)

- `models/SchGen-merged-hf/` - the surgically-assembled merged HF checkpoint (21 layers untouched MXFP4, 3 layers merged dense)
- `models/SchGen-merged.gguf` - the converted GGUF (17.3GB, bf16 for merged layers + native MXFP4 for the rest)
- `llama.cpp/` (gitignored, cloned fresh) - upstream conversion tooling, specifically `conversion/gpt_oss.py`
- `.venv-gguf-convert/` (gitignored, isolated venv) - kept separate from the main venv specifically to avoid the conversion script's CPU-only `torch==2.11.0` pin clobbering the main venv's working GPU torch
- Ollama model `schgen-merged-test` - the served result
- `SchGen/schematic_generation/verify_and_retry_ollama.py` - the retry loop for the Ollama-served path, proven on the regulator prompt above

## Still open before this is a finished Work Item

- Only 3 prompts tested total. Broader domain coverage (matching the variety Layer 1's own testing used) would build more confidence.
- Merged layers are bf16, not requantized down to match the rest of the model's compactness (e.g. Q4_K_M) - that would need its own correctness check, same rigor as the orientation bug caught here.
- No decision yet on whether this should replace `generate.py`'s PyTorch path in normal use, or coexist as an alternative - that's a Sponsor call, not a technical blocker.

## Common mistakes to avoid

- Don't trust "the merge ran without crashing" or "the top predicted token still looks right" as evidence of correctness on its own - localize any observed difference (e.g. via routing/weight-level checks) before concluding a merge is broken; the first pass here overcalled a real MoE-routing-sensitivity effect as a bug.
- Don't assume dequantizing a module's *weights* also changes how PEFT (or any tool) treats its *class* - the warning fired because the class was still `Mxfp4GptOssExperts` even after its parameters were replaced with plain dequantized values.

## Code references

- `evidence/T002-merge-numeric-verification.log` - the real test run and its output
- `models/SchGen-adapter/adapter_config.json` - the real adapter structure (target_modules + target_parameters)
- `SchGen/schematic_generation/generate.py` - the existing, working, hand-rolled MXFP4 dequant approach this test's loading code reused
