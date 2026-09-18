"""
Step 6 (T001): end-to-end test of the full Layer 1 pipeline (retrieval ->
generate-with-retry -> hallucination filter -> real verify -> score -> rank)
on several vague prompts spanning different circuit domains that plausibly
match real components in the 241-component open-schematics KG.

Domains chosen based on a real keyword scan of the KG (not assumed):
LED/indicator (proven in the retry-loop test), current sensing (INA240A1/
ACS37010), OLED display (SSD1306), and USB charging (TP4056 - this domain
was already flagged in skills/layer1-pipeline/SKILL.md as having a retrieval
quirk where CP2102N, a USB-UART bridge, can outrank the actual charger; kept
in this test deliberately to see whether the full pipeline still resolves
it correctly downstream of retrieval).

Deliberately avoids the "connect two boards with a cable" style of prompt -
already confirmed via test_retrieval.py that this KG has zero generic
connectors (only 3 USB connectors total), so no retrieval algorithm could
surface a match; that's a documented KG gap, not something this test should
re-discover.

Per the task spec: prints each candidate's name, summary, verification_status
and errors per prompt, and explicitly flags any "rejected" status (since that
means a hallucination slipped past the prompt-level constraints and was only
caught by the deterministic filter, not by generation quality itself).
"""

import sys

sys.path.insert(0, "/scratch/k2983/PCBSchemaGen_v2")
from kg_open_schematics_store import OpenSchematicsKGStore
from pipeline import run_layer1
from generate_candidates import check_headroom_or_raise

TEST_PROMPTS = [
    "I need something to blink an LED",
    "add a way to measure current",
    "I want a small OLED display for status info",
    "something for charging a phone over USB",
]

N_CANDIDATES = 2
MAX_ATTEMPTS = 3


def main():
    check_headroom_or_raise()
    kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/PCBSchemaGen_v2")

    any_rejected = False
    summary = []  # (prompt, [ (candidate_id, status) ])

    for prompt in TEST_PROMPTS:
        print("=" * 70)
        print(f"PROMPT: {prompt!r}")
        print("=" * 70)

        result = run_layer1(prompt, kg, n=N_CANDIDATES, max_attempts=MAX_ATTEMPTS)
        per_prompt = []

        for c in result["ranked"]:
            status = c.get("verification_status")
            per_prompt.append((c.get("id"), status))
            print(f"- id={c.get('id')!r} name={c.get('name')!r}")
            print(f"  summary: {c.get('summary')}")
            print(f"  verification_status: {status}  (attempts={c.get('_attempts')}, score={c.get('score'):.3f})")
            errors = c.get("verification_errors")
            if errors:
                print(f"  errors: {errors}")
            if status == "rejected":
                any_rejected = True
                print("  *** FLAGGED: rejected - a hallucination slipped past prompt-level "
                      "constraints and was only caught by the deterministic filter. ***")
            print()

        summary.append((prompt, per_prompt))

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total = passed = failed_checks = rejected = 0
    for prompt, candidates in summary:
        for cid, status in candidates:
            total += 1
            if status == "passed":
                passed += 1
            elif status == "failed_checks":
                failed_checks += 1
            elif status == "rejected":
                rejected += 1
    print(f"total candidates: {total}  passed: {passed}  failed_checks: {failed_checks}  rejected: {rejected}")

    if any_rejected:
        print("\n*** AT LEAST ONE CANDIDATE WAS REJECTED ACROSS THESE TEST RUNS. ***")
        print("This means a hallucination slipped past the prompt-level constraints")
        print("(the system prompt's allowed vocabulary) and was only caught by")
        print("Step 3's deterministic fact-check filter, not by generation quality.")
    else:
        print("\nNo rejected candidates across all test runs - every candidate the")
        print("retry loop returned was either a real pass or a real (non-hallucinated)")
        print("failed_checks result from the deterministic verifier.")

    return summary, any_rejected


if __name__ == "__main__":
    main()
