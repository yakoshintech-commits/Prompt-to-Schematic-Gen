"""
Constrained candidate generator: retrieves the allowed component vocabulary,
then sends one LLM call whose system prompt provides that vocabulary as the
ONLY allowed set, and explicitly forbids inventing any part_id/pin_id/pin_name
not present verbatim in it. Per T001 Step 2.

Model choice (llama3.1:8b via Ollama) and the GPU headroom check pattern are
confirmed and documented in skills/local-llm-setup/SKILL.md and
skills/schgen-integration/SKILL.md respectively - see those for the real
comparison-test evidence behind these choices, not just this file's code.
"""

import json
import subprocess

import requests

from prompts import build_system_prompt, build_user_prompt
from retrieval import retrieve_relevant_components

MODEL_NAME = "llama3.1:8b"
OLLAMA_URL = "http://localhost:11434/api/chat"
MIN_HEADROOM_GB = 3.0  # "several gigabytes of margin, not just the bare minimum" per the task spec


def gpu_headroom_gb() -> float:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    )
    used, total = (int(x.strip()) for x in result.stdout.strip().split(","))
    return (total - used) / 1024


def check_headroom_or_raise(model_name: str = MODEL_NAME):
    headroom = gpu_headroom_gb()
    if headroom < MIN_HEADROOM_GB:
        raise RuntimeError(
            f"Refusing to run {model_name}: only {headroom:.1f} GB free, "
            f"need at least {MIN_HEADROOM_GB} GB margin. SchGen or another "
            f"process may be using the GPU - check `nvidia-smi` before retrying."
        )


def _parse_candidate_json(raw: str) -> dict:
    """Defensive parse: strip markdown fences if present, surface real errors clearly."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Model did not return valid JSON for a candidate. "
            f"Parse error: {e}. Raw response (first 500 chars): {raw[:500]!r}"
        ) from e


def _call_model(system_prompt: str, user_prompt: str) -> str:
    check_headroom_or_raise()
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def generate_candidates(vague_prompt: str, kg_store, n: int = 4) -> list[dict]:
    """
    Retrieve relevant real components, then ask the local model for up to n
    circuit candidates grounded ONLY in that vocabulary. Each returned dict
    matches the candidate schema (id, name, summary, tradeoffs, assumptions,
    components, nets) - not yet fact-checked (that's Step 3) or verified
    (Step 4), just what the model produced.
    """
    allowed_components = retrieve_relevant_components(vague_prompt, kg_store, top_k=15)
    allowed_json = json.dumps(allowed_components, indent=2)

    system_prompt = build_system_prompt(allowed_json)
    user_prompt = build_user_prompt(vague_prompt) + f"\n\nPropose {n} architecturally distinct candidates as a JSON array of {n} candidate objects, not a single object."

    raw = _call_model(system_prompt, user_prompt)
    parsed = _parse_candidate_json(raw)

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise ValueError(f"Expected a JSON array of candidates, got {type(parsed).__name__}: {raw[:300]!r}")

    return parsed
