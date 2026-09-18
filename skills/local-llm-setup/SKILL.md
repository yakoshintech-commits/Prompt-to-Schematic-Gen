# Local LLM Setup

## Purpose

Which local model/runtime Layer 1's generation step uses, why, and GPU safety notes for coexisting with SchGen on a shared GPU.

## Key facts (confirmed empirically, not assumed)

**Model choice: `llama3.1:8b` via Ollama - confirmed via a real head-to-head test, not just followed as the spec's suggested default.** Compared against `deepseek-coder:33b` (already pulled for this portfolio's "code execution" role, per `context.md`'s Model Assignment) on this exact task: strict-JSON candidate generation constrained to a small allowed-component vocabulary.

- **Simple case** (2-component vocabulary, request fully satisfiable): both models produced valid JSON, correct schema, zero hallucinated part_ids/pins. No difference.
- **Hard case** (same 2-component vocabulary - just R and LED - asked to "regulate 12V down to 3.3V", which neither R nor LED can really do): `llama3.1:8b` correctly stayed within the vocabulary (improvised a resistor-based workaround using only R/LED, no invented part_id). `deepseek-coder:33b` **invented `"IC1"`** as a part_id - a fabricated component not present anywhere in the allowed vocabulary, despite the system prompt's explicit "CRITICAL RULES" forbidding exactly this. This is the single property that matters most for this role (grounding, not raw generation quality), so `llama3.1:8b` is the confirmed choice, not just the unverified default.
- `deepseek-coder:33b` was faster in these tests (8.5-8.8s vs `llama3.1:8b`'s 4.9-23.9s), but speed doesn't matter if the output can't be trusted without a hallucination it should never have produced given how explicit the constraint was.

**Exact API call shape** (Ollama's local HTTP API, `POST http://localhost:11434/api/chat`):
```python
requests.post("http://localhost:11434/api/chat", json={
    "model": "llama3.1:8b",
    "messages": [
        {"role": "system", "content": system_prompt},  # allowed-vocabulary JSON + rules
        {"role": "user", "content": user_prompt},        # the vague request
    ],
    "stream": False,
    "options": {"temperature": 0},
})
# response: resp.json()["message"]["content"] - a string, strip markdown fences before json.loads
```

**Pull command**: `ollama pull llama3.1:8b` (one-time; already run for this project - `ollama list` will show it if present, skip re-pulling).

**Measured VRAM footprint**: **9.2 GB**, confirmed via `ollama ps` while loaded (`nvidia-smi` before/after a call showed a 22751 -> 9367 MiB delta, matching). This is with Ollama's default 32768-token context window. Ollama unloads an idle model after its default keep-alive window (observed: a few minutes) and loads whichever model is next requested - it does not necessarily keep multiple models resident simultaneously, so don't assume `deepseek-coder:33b` stays loaded once `llama3.1:8b` gets used, or vice versa.

**GPU coexistence math, the reason the headroom check is not optional**: SchGen's own generation model uses roughly 17-25GB VRAM when actively loaded (confirmed via `generate.py`'s own `_mem_checkpoint` logging in the SchGen hardening work - see `SchGen/schematic_generation/generate.py`). `llama3.1:8b`'s 9.2GB **can push the combined total over the shared 32GB GPU's capacity** if both happen to be loaded at once. This is not a theoretical concern - it's the same class of real CUDA OOM already hit and root-caused once this session (see `skills/schgen-integration/SKILL.md`'s "Coexisting safely with SchGen" section for the actual check pattern).

## Common mistakes to avoid

- Don't skip the pre-call GPU headroom check because "it's just an 8B model" - 9.2GB is still enough to collide with SchGen's own 17-25GB footprint on a 32GB GPU.
- Don't assume the faster/larger model is the better choice for a grounding-critical task - `deepseek-coder:33b` was faster but hallucinated a part_id under the exact condition (vocabulary gap) this system is designed to prevent.
- Don't trust the model's own claim that it "used only the allowed components" - always run the actual result through Step 3's deterministic `validate_facts.py` check regardless of which local model was used.

## Code references

- `layer1/compare_local_models.py` - the simple-case comparison
- `layer1/compare_local_models_hard.py` - the hard-case comparison that surfaced the deepseek-coder hallucination
- `layer1/prompts.py` - `build_system_prompt`, `build_user_prompt` (the constrained-vocabulary prompt text)
- `layer1/generate_candidates.py` - the actual generator using this model
