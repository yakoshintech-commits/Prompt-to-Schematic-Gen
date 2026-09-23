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


MAX_SCHEMA_PIN_CHOICES = 120  # see build_candidate_schema's docstring


def build_candidate_schema(allowed_components: list[dict]) -> dict:
    """
    Dynamic per-request JSON schema (Ollama's `format` param, converted
    internally to a constrained grammar) built from the REAL retrieved
    component list. Confirmed empirically (2026-09-18) against a real
    Ollama 0.34.1 instance that per-field enums (part_id enum + separate
    pin_id enum + separate pin_name enum) let the model assemble a
    syntactically-valid but semantically-wrong combination (e.g. pin_id="1"
    paired with pin_name="VIN+", which isn't a real INA226 pin - VIN+ is
    actually pin 8). Fixed by using ONE composite enum per real pin
    ("<part_id>::<pin_id>::<pin_name>") so the model can only choose an
    atomic, real (part_id, pin_id, pin_name) triple - not assemble a
    fabricated one from independently-valid pieces. This eliminates the
    "invents a nonexistent part/pin" hallucination class structurally; it
    does NOT guarantee the model picks the semantically correct real pin
    for the task (still possible to pick a real-but-wrong pin) - that's
    still validate_facts.py / verify_candidate.py's job, unchanged.

    maxItems bounds on components/nets/endpoints are load-bearing, not
    cosmetic - confirmed empirically (2026-09-18): without them, one real
    call (a schema with 120 pin choices, well within the budget below) ran
    for 500+s at a sustained 96-97% GPU utilization without ever returning
    (confirmed via a background nvidia-smi monitor - genuinely computing,
    not hung). Most likely cause: an unbounded array combined with
    grammar-constrained greedy (temperature=0) decoding gives the model no
    natural incentive to close the array, so it can loop through valid
    enum choices far longer than any real circuit candidate needs. A
    sensible real PCB candidate uses a handful of components/nets, so
    capping array length costs nothing real and removes the runaway risk.
    """
    # Grammar-constrained decoding cost scales with enum size - confirmed
    # empirically (2026-09-18): "something for charging a phone over USB"
    # pulled 2 devboards (nice_nano_raw21, ESP32-S3-DevKitC) into its
    # retrieved top-15, ballooning the pin-choice enum to 208 entries vs
    # ~107 for a domain without devboards, and the real Ollama call timed
    # out at 300s where the smaller-enum prompt succeeded well under it.
    # Cap the PIN budget (not component count, since one devboard alone can
    # account for the whole blowup) by including components in retrieval-
    # score order until the budget's spent, skipping (not truncating) any
    # single component that alone would bust it - keeps smaller relevant
    # components reachable even if a large one sorted ahead of them.
    part_ids = []
    pin_choices = []
    for c in allowed_components:
        comp_pins = [f"{c['id']}::{pin['num']}::{pin['name']}" for pin in c.get("pins", [])]
        if pin_choices and len(pin_choices) + len(comp_pins) > MAX_SCHEMA_PIN_CHOICES:
            continue
        part_ids.append(c["id"])
        pin_choices.extend(comp_pins)

    return {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "summary": {"type": "string"},
            "tradeoffs": {"type": "string"},
            "assumptions": {"type": "string"},
            "components": {
                "type": "array",
                "maxItems": 8,  # unbounded arrays + grammar-constrained enums can runaway-loop, see below
                "items": {
                    "type": "object",
                    "properties": {
                        "ref": {"type": "string"},
                        "part_id": {"type": "string", "enum": part_ids},
                    },
                    "required": ["ref", "part_id"],
                },
            },
            "nets": {
                "type": "array",
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "endpoints": {
                            "type": "array",
                            "maxItems": 6,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "ref": {"type": "string"},
                                    "pin_choice": {"type": "string", "enum": pin_choices},
                                },
                                "required": ["ref", "pin_choice"],
                            },
                        },
                    },
                    "required": ["name", "endpoints"],
                },
            },
        },
        "required": ["id", "name", "summary", "components", "nets"],
    }


def _expand_pin_choices(candidate: dict) -> dict:
    """
    Reverses build_candidate_schema's composite pin_choice encoding back
    into pin_id/pin_name, so everything downstream (validate_facts.py,
    verify_candidate.py) sees the same candidate shape it always has -
    the schema-constraint trick is local to generation, not a format
    change the rest of the pipeline needs to know about.
    """
    for net in candidate.get("nets", []):
        for endpoint in net.get("endpoints", []):
            choice = endpoint.pop("pin_choice", None)
            if choice is not None:
                _part, pin_id, pin_name = choice.split("::", 2)
                endpoint["pin_id"] = pin_id
                endpoint["pin_name"] = pin_name
    return candidate


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


def _call_model(messages: list[dict], format_schema: dict | None = None,
                 temperature: float = 0, seed: int | None = None) -> str:
    check_headroom_or_raise()
    # temperature=0 (greedy) is fully deterministic here - confirmed
    # empirically (2026-09-23): 3 repeated calls with identical messages
    # returned byte-identical output. That matters for multi-candidate
    # sampling (generate_verified_candidates' n>1): calling this n times
    # with temperature=0 does NOT produce n different candidates, it just
    # repeats the same deterministic generate-and-retry chain n times for
    # zero benefit - real diversity requires temperature>0 with a distinct
    # seed per slot (also confirmed empirically: 4 calls at temp=0.8 with
    # distinct seeds returned 4 distinct, still schema-valid candidates).
    options = {"temperature": temperature, "num_predict": 1500}
    if seed is not None:
        options["seed"] = seed
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        # num_predict: hard safety net independent of maxItems working -
        # a real candidate's JSON is well under this; see
        # build_candidate_schema's docstring for the runaway-generation
        # failure this guards against.
        "options": options,
    }
    if format_schema is not None:
        payload["format"] = format_schema
    resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
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


def _generate_one(system_prompt: str, user_prompt: str, feedback: str | None, prev_response: str | None,
                   format_schema: dict | None = None, temperature: float = 0, seed: int | None = None) -> tuple[dict, str]:
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

    raw = _call_model(messages, format_schema=format_schema, temperature=temperature, seed=seed)
    parsed = _parse_candidate_json(raw)
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    if format_schema is not None:
        parsed = _expand_pin_choices(parsed)
    return parsed, raw


def generate_one_verified_candidate(vague_prompt: str, kg_store, allowed_json: str, max_attempts: int = 3,
                                     allowed_components: list[dict] | None = None,
                                     temperature: float = 0, seed: int | None = None) -> dict:
    """
    Generate ONE candidate, verify it, and on failure feed the real error
    back for another attempt (up to max_attempts) before giving up and
    returning the last attempt's result as-is (still carrying its real
    verification_status/errors). Mirrors the verify-and-retry pattern
    already proven for SchGen this session - Layer 1's own generation step
    needed the same thing, not just Step 3/4's ability to detect failure.

    temperature/seed are held constant across every attempt within THIS
    slot's retry chain - confirmed necessary (2026-09-23): temperature=0
    is fully deterministic, so a slot's own attempt-2/3 already diverges
    naturally from attempt-1 via the real feedback text added to the
    conversation; there's no need to also vary temperature mid-chain, and
    keeping it fixed per-slot is what makes each slot's overall trajectory
    reproducible for testing/debugging while still differing SLOT to SLOT.
    """
    from verify_candidate import verify_candidate  # local import: avoids a cycle at module load time

    system_prompt = build_system_prompt(allowed_json)
    user_prompt = build_user_prompt(vague_prompt)
    format_schema = build_candidate_schema(allowed_components) if allowed_components else None

    feedback = None
    prev_response = None
    candidate = {}

    for attempt in range(1, max_attempts + 1):
        candidate, raw = _generate_one(system_prompt, user_prompt, feedback, prev_response,
                                        format_schema=format_schema, temperature=temperature, seed=seed)
        verify_candidate(candidate, kg_store)
        candidate["_attempts"] = attempt

        if candidate.get("verification_status") == "passed":
            return candidate

        feedback = "\n".join(candidate.get("verification_errors") or ["Unknown verification failure."])
        prev_response = raw

    return candidate


# Applied to every candidate SLOT after the first when generate_verified_
# candidates(n>1) samples for diversity - confirmed necessary (2026-09-23):
# temperature=0 is fully deterministic (byte-identical output across
# repeated identical calls), so without this, additional slots would just
# re-run the exact same deterministic chain n times for zero benefit.
# 0.8 is not tuned against a held-out set - a standard "meaningfully
# diverse but not incoherent" value, chosen because this needed a real
# value to test with, not because it's been swept.
_DIVERSITY_TEMPERATURE = 0.8


def generate_verified_candidates(vague_prompt: str, kg_store, n: int = 4, max_attempts: int = 3) -> list[dict]:
    """
    Generate n architecturally-distinct candidate SLOTS, each with its own
    verify-and-retry budget (up to max_attempts). Retrieval is computed once
    and shared across all slots/attempts, since it only depends on
    vague_prompt. Unlike generate_candidates (one shot, N candidates in one
    call), this actually tries to get each slot to a real pass, not just to
    a plausible-looking first draft.

    Slot 0 always uses temperature=0 (identical to this function's
    long-standing behavior at n=1 - zero regression risk to any
    already-tested single-candidate result). Slots 1..n-1 use
    _DIVERSITY_TEMPERATURE with a distinct, fixed seed per slot, so
    multiple slots have a real chance of exploring different completions
    instead of repeating the same deterministic chain - see _call_model's
    docstring comment for the empirical confirmation this was necessary.
    """
    allowed_components = retrieve_relevant_components(vague_prompt, kg_store, top_k=15)
    allowed_json = json.dumps(allowed_components, indent=2)

    return [
        generate_one_verified_candidate(
            vague_prompt, kg_store, allowed_json, max_attempts=max_attempts,
            allowed_components=allowed_components,
            temperature=(0 if i == 0 else _DIVERSITY_TEMPERATURE),
            seed=(None if i == 0 else i),
        )
        for i in range(n)
    ]
