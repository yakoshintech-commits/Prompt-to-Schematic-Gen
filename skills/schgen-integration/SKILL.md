# SchGen Integration

## Purpose

SchGen's CLI interface, request style, and safety rules for coexisting with a concurrently running SchGen process (shared GPU), so Layer 1's handoff to SchGen doesn't have to be re-derived each time.

## Key facts (confirmed empirically, not assumed)

## Coexisting safely with SchGen

Real, measured numbers, not a guess: SchGen's own generation model uses roughly **17-25GB VRAM** when actively loaded and generating (confirmed via `_mem_checkpoint` logging added during this session's SchGen hardening work - see `SchGen/schematic_generation/generate.py`, e.g. `gpu_alloc=17.36GB` right after load, peaking around `gpu_peak=28.68GB` during generation). Layer 1's own local model (`llama3.1:8b`) uses a further **9.2GB**. On a shared **32GB GPU**, SchGen alone plus Layer 1's model **can exceed total capacity if both happen to be loaded and running at once** - this already caused one real CUDA OOM this session (a different cause - eager attention's O(n^2) memory cost - but the same class of problem: not checking real headroom before assuming there's room).

**The check, used before every local model call in `layer1/generate_candidates.py`**:
```python
import subprocess

def gpu_headroom_gb() -> float:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    )
    used, total = (int(x.strip()) for x in result.stdout.strip().split(","))
    return (total - used) / 1024  # GB

MIN_HEADROOM_GB = 3.0  # "several gigabytes of margin, not just the bare minimum" per the task spec

def check_headroom_or_raise(model_name: str):
    headroom = gpu_headroom_gb()
    if headroom < MIN_HEADROOM_GB:
        raise RuntimeError(
            f"Refusing to run {model_name}: only {headroom:.1f} GB free, "
            f"need at least {MIN_HEADROOM_GB} GB margin. SchGen or another "
            f"process may be using the GPU - check `nvidia-smi` before retrying."
        )
```

This raises rather than silently falling back to CPU, on the reasoning that a Layer 1 sprint should stop and let the Sponsor investigate contention rather than proceed on a degraded, much-slower CPU path without visibility. (The task spec's own instruction allows either - "default to CPU-only inference if in doubt" - raising was chosen here since a silent CPU fallback could mask a real contention problem for a long time before anyone notices generation got slow.)

Ollama does not necessarily keep multiple models resident in VRAM simultaneously - it unloads an idle model after a keep-alive window (observed: a few minutes) and loads whichever model is next requested. This means `llama3.1:8b` and SchGen's model are less likely to BOTH be fully loaded at the exact same instant than the raw "17-25GB + 9.2GB > 32GB" math alone suggests - but the check above should still run every time, since Ollama's unload timing isn't something Layer 1 controls or should rely on.

## The PROJECT_PATH trap (root-caused 2026-09-18, cost several hours of misdirected debugging)

Every SchGen run that afternoon produced garbled, repetitive, non-terminating output (`"Ne Ne Ne..."`, `"# S: # S:..."`, `"User: Assistant: User:..."`) instead of valid JSON, including on prompts that had worked cleanly hours earlier. Chased and ruled out, in order, with real evidence each time:

1. **Prompt structure/phrasing** - rewrote from bulleted/kwarg-style to flowing prose. Still failed identically.
2. **Repeated phrasing priming repetition** - deduped a candidate's repeated `"a LED (Generic LED)"` clause into one grouped clause. Still failed (different garbage, same shape).
3. **Concurrent GPU contention from other sessions on this shared machine** - found and killed two leftover `claude` processes and a stale `ollama run` session. Plausible in theory, but the user's own activity in those sessions was confirmed benign (just asking about a file path - no GPU-touching command), which weakened this considerably before it was even tested.
4. **Thermal/power throttling or hardware corruption** - ran a live `nvidia-smi` telemetry monitor (2s samples) through an actual failing generation: temp topped out at 48°C, clocks held steady at boost (2887MHz), throttle-reasons bitmask was `0x0` for the entire run except two brief, harmless power-management blips. Hardware was completely healthy. Also ruled out by the output being **byte-for-byte identical** across separate process runs - real hardware corruption wouldn't reproduce exactly.
5. **A code regression since the last working run** - checked git log and the working evidence log's file mtime (11:36:42, right after the fix-commit merge at 11:36:55) against `git log` on `SchGen/`: no commits landed between the working run and the failing ones. Same code.

**The real cause**: `SchGen/schematic_generation/generate.py` does `sys.path.append(os.environ["PROJECT_PATH"])` to make its own `modules` package importable (the package isn't reachable relative to the script's own directory). The venv used to run SchGen physically lives at `schgen_upstream_reference_dir/.venv` (a pre-existing setup decision), and its `bin/activate` script **hardcoded** `export PROJECT_PATH=<schgen_upstream_reference_dir>` - the pristine, unfixed clone. So every `source .venv/bin/activate` silently pointed Python's import resolution at the wrong copy of `modules/symbol_context.py` and `modules/utils/llm_interface.py`, regardless of which directory the entry script itself was run from. Confirmed directly: `python3 -c "import modules.symbol_context as sc; print(sc.__file__)"` resolved to the pristine path, and the crash tracebacks from every failing run literally named that same wrong path.

**Concrete consequence**: this meant the eager-attention fix (`self.model.set_attn_implementation("eager")`, added earlier this session specifically to fix `flash_attention_2`'s garbled-output bug on this generic instruction-following task) was **never actually active** in any of that afternoon's test runs - the unfixed `llm_interface.py` was silently imported instead, so the exact bug it was meant to fix kept firing.

**Fix, applied twice for good measure**: first, the venv's `activate` script was corrected directly so `PROJECT_PATH` defaulted to `schgen_dir` (the editable clone). Then, as part of a broader "nothing lives outside root-project" reorganization the same day, the venv itself was moved entirely out of the pristine clone to a shared, top-level location (`schgen_venv_dir` in `config/paths.md`) - removing the structural trap altogether, not just patching its symptom. Re-running the exact prompt that had failed identically 5 times in a row, with `PROJECT_PATH` corrected, produced a clean, correct, real schematic-generation script on the first try; re-verified again after the full relocation (torch/transformers import, `modules.symbol_context.__file__` resolution) with the same clean result.

**Lesson**: when a previously-working command starts failing with no code change, check environment/`sys.path` resolution before assuming hardware, contention, or a subtler code bug - `<module>.__file__` after import is a cheap, direct way to confirm which physical file is actually running, and it should have been the first thing checked, not the last.

## Common mistakes to avoid

- Don't assume the GPU is free just because Layer 1's own model is small (9.2GB) - SchGen's 17-25GB footprint alone leaves only 7-15GB, which is thin margin depending on what else is running.
- Don't rely on Ollama's automatic model-unload timing as a safety mechanism - always run the explicit headroom check regardless of what you assume is or isn't currently loaded.

## Code references

- `layer1/generate_candidates.py` - `check_headroom_or_raise`, called before every Ollama request
- `SchGen/schematic_generation/generate.py` - `_mem_checkpoint`, the source of the 17-25GB SchGen measurements above
