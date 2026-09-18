"""
Converts a Layer 1 verified JSON candidate into the detailed natural-language
prompt SchGen's generate.py --test_raw --prompt expects. This is the one
missing connector between "vague prompt -> verified JSON candidate" (Layer 1,
already built and tested) and "detailed prompt -> real schematic" (SchGen,
already built and tested).

Since the candidate is already fully grounded (every part_id/pin_id/pin_name
checked against real data) and SchGenCompatibleKGStore already knows the
exact stock KiCad symbol_lib each part_id lives in, the generated prompt
names the exact symbol_lib/symbol_name/pin for every component and
connection explicitly - stronger grounding transfer than a purely
descriptive prompt, since SchGen's own symbol search doesn't have to guess
which library or literal part to reach for.
"""


def candidate_to_detailed_prompt(candidate: dict, kg_store) -> str:
    """
    Flowing natural-language prose, NOT a structured/bulleted list - confirmed
    necessary (2026-09-18): a first version using bullet points and embedded
    symbol_lib="X" kwarg-style syntax caused SchGen's local model to
    degenerate into repetitive garbage output across all 3 retry attempts on
    the symbol-selection step, never reaching code generation. The one prompt
    style already proven to work this session (the real USB-C breakout test)
    was a single flowing paragraph in plain English - SchGen's fine-tuning
    data is presumably shaped like that, not like an itemized spec sheet, so
    this reproduces that shape while keeping every exact real value (part
    name, pin id/name) Layer 1 already verified.
    """
    # Group refs sharing the same part_id into ONE clause instead of one per
    # ref - confirmed necessary (2026-09-18): a candidate using the same
    # part_id for 3 different refs produced a prompt repeating an identical
    # phrase ("a LED (Generic LED)") 3 times in a row, and SchGen's local
    # model degenerated into repetitive garbage output on that prompt across
    # all 3 retry attempts - a known LM failure mode where repetitive input
    # primes repetitive, non-terminating output under greedy decoding. Same
    # underlying facts, just not repeated verbatim in the prompt text.
    by_part = {}
    order = []
    for comp in candidate.get("components", []):
        part_id = comp["part_id"]
        if part_id not in by_part:
            by_part[part_id] = []
            order.append(part_id)
        by_part[part_id].append(comp["ref"])

    comp_phrases = []
    for part_id in order:
        refs = by_part[part_id]
        note = (kg_store.get_component(part_id) or {}).get("note", "")
        desc = f"a {part_id} ({note})" if note else f"a {part_id}"
        if len(refs) == 1:
            comp_phrases.append(f"{refs[0]} as {desc}")
        else:
            ref_list = ", ".join(refs[:-1]) + f", and {refs[-1]}"
            comp_phrases.append(f"{ref_list} as {len(refs)} separate instances of {desc}")

    conn_phrases = []
    for net in candidate.get("nets", []):
        endpoints = net.get("endpoints", [])
        if len(endpoints) < 2:
            continue
        pin_strs = [f"{ep['ref']}'s {ep['pin_name']} pin (pin {ep['pin_id']})" for ep in endpoints]
        conn_phrases.append(" to ".join(pin_strs))

    summary = candidate.get("summary") or candidate.get("name") or "a small circuit"
    prompt = f"Design a schematic for {summary} Use exactly these real components: " + \
        ", ".join(comp_phrases) + ". Do not substitute or invent a different part for any of them."
    if conn_phrases:
        prompt += " Wire it up as follows: connect " + "; connect ".join(conn_phrases) + "."
    if candidate.get("assumptions"):
        prompt += f" {candidate['assumptions']}"

    return prompt
