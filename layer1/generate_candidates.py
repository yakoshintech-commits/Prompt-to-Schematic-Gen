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

from prompts import build_system_prompt, build_user_prompt, build_feedback_prompt
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


def _call_model(messages: list[dict]) -> str:
    check_headroom_or_raise()
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "messages": messages,
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
    circuit candidates grounded ONLY in that vocabulary in a single call.
    Each returned dict matches the candidate schema - not yet fact-checked
    or verified. Kept for the original Step 2 one-shot use case; see
    generate_verified_candidates for the retry-loop version that actually
    checks each candidate and tries again on failure - confirmed necessary,
    not optional, after every candidate from this one-shot version failed
    verification across every real test run this session (documented in
    skills/layer1-pipeline/SKILL.md).
    """
    allowed_components = retrieve_relevant_components(vague_prompt, kg_store, top_k=15)
    allowed_json = json.dumps(allowed_components, indent=2)

    system_prompt = build_system_prompt(allowed_json)
    user_prompt = build_user_prompt(vague_prompt) + f"\n\nPropose {n} architecturally distinct candidates as a JSON array of {n} candidate objects, not a single object."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = _call_model(messages)
    parsed = _parse_candidate_json(raw)

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise ValueError(f"Expected a JSON array of candidates, got {type(parsed).__name__}: {raw[:300]!r}")

    return parsed


def _generate_one(system_prompt: str, user_prompt: str, feedback: str | None, prev_response: str | None) -> tuple[dict, str]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    if feedback and prev_response:
        # Real multi-turn correction (assistant's own prior attempt, then a
        # genuine user reply), not a second back-to-back user message - see
        # build_feedback_prompt's docstring for why this structure matters.
        messages.append({"role": "assistant", "content": prev_response})
        messages.append({"role": "user", "content": build_feedback_prompt(feedback)})

    raw = _call_model(messages)
    parsed = _parse_candidate_json(raw)
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    return parsed, raw


def generate_one_verified_candidate(vague_prompt: str, kg_store, allowed_json: str, max_attempts: int = 3) -> dict:
    """
    Generate ONE candidate, verify it, and on failure feed the real error
    back for another attempt (up to max_attempts) before giving up and
    returning the last attempt's result as-is (still carrying its real
    verification_status/errors). Mirrors the verify-and-retry pattern
    already proven for SchGen this session - Layer 1's own generation step
    needed the same thing, not just Step 3/4's ability to detect failure.
    """
    from verify_candidate import verify_candidate  # local import: avoids a cycle at module load time

    system_prompt = build_system_prompt(allowed_json)
    user_prompt = build_user_prompt(vague_prompt)

    feedback = None
    prev_response = None
    candidate = {}

    for attempt in range(1, max_attempts + 1):
        candidate, raw = _generate_one(system_prompt, user_prompt, feedback, prev_response)
        verify_candidate(candidate, kg_store)
        candidate["_attempts"] = attempt

        if candidate.get("verification_status") == "passed":
            return candidate

        feedback = "\n".join(candidate.get("verification_errors") or ["Unknown verification failure."])
        prev_response = raw

    return candidate


def generate_verified_candidates(vague_prompt: str, kg_store, n: int = 4, max_attempts: int = 3) -> list[dict]:
    """
    Generate n architecturally-distinct candidate SLOTS, each with its own
    verify-and-retry budget (up to max_attempts). Retrieval is computed once
    and shared across all slots/attempts, since it only depends on
    vague_prompt. Unlike generate_candidates (one shot, N candidates in one
    call), this actually tries to get each slot to a real pass, not just to
    a plausible-looking first draft.
    """
    allowed_components = retrieve_relevant_components(vague_prompt, kg_store, top_k=15)
    allowed_json = json.dumps(allowed_components, indent=2)

    return [
        generate_one_verified_candidate(vague_prompt, kg_store, allowed_json, max_attempts=max_attempts)
        for _ in range(n)
    ]
