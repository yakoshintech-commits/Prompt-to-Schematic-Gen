"""
Orchestration + scoring: calls the retry-verified generator, computes a
deterministic weighted score, and returns both the full candidate list and
a ranked list. Does NOT auto-pick a winner. Per T001 Step 5.

Uses generate_verified_candidates (generate -> verify -> retry-with-real-
feedback per candidate slot), not the older one-shot generate_candidates -
every candidate from the one-shot version failed verification across every
real test run this session (see skills/layer1-pipeline/SKILL.md), the same
shape of problem SchGen had before its own verify-and-retry loop existed.
"""

from generate_candidates import generate_verified_candidates

DEFAULT_WEIGHTS = {"cost": 0.4, "simplicity": 0.3, "part_availability": 0.3}


def _score_candidate(candidate: dict, weights: dict) -> float:
    n_components = len(candidate.get("components", []))
    simplicity = 1.0 / (1 + n_components)  # inverse function of component count

    part_availability = 1.0 if candidate.get("verification_status") == "passed" else 0.0

    # Placeholder - same value for every candidate until there's a real
    # BOM cost lookup. TODO: wire in real bill-of-materials cost lookup.
    cost = 0.5

    return (
        weights.get("cost", 0) * cost
        + weights.get("simplicity", 0) * simplicity
        + weights.get("part_availability", 0) * part_availability
    )


def run_layer1(vague_prompt: str, kg_store, n: int = 4, weights: dict | None = None, max_attempts: int = 3) -> dict:
    """
    Runs the full Layer 1 pipeline: generate-with-retry -> score -> rank.
    Returns {"candidates": [...], "ranked": [...]} - the ranked list always
    puts verification-passed candidates above failed_checks/rejected ones,
    regardless of score; within each group, higher score ranks first. Does
    not auto-pick a winner - that's the Sponsor's / a future UI's call.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    candidates = generate_verified_candidates(vague_prompt, kg_store, n=n, max_attempts=max_attempts)
    for candidate in candidates:
        candidate["score"] = _score_candidate(candidate, weights)

    def rank_key(c):
        status_priority = 0 if c.get("verification_status") == "passed" else 1
        return (status_priority, -c.get("score", 0))

    ranked = sorted(candidates, key=rank_key)

    return {"candidates": candidates, "ranked": ranked}
