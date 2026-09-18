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

## Common mistakes to avoid

- Don't assume the GPU is free just because Layer 1's own model is small (9.2GB) - SchGen's 17-25GB footprint alone leaves only 7-15GB, which is thin margin depending on what else is running.
- Don't rely on Ollama's automatic model-unload timing as a safety mechanism - always run the explicit headroom check regardless of what you assume is or isn't currently loaded.

## Code references

- `layer1/generate_candidates.py` - `check_headroom_or_raise`, called before every Ollama request
- `SchGen/schematic_generation/generate.py` - `_mem_checkpoint`, the source of the 17-25GB SchGen measurements above
