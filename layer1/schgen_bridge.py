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
        component = kg_store.get_component(part_id) or {}
        note = component.get("note", "")
        # Include the real stock KiCad library name explicitly - confirmed
        # necessary (2026-09-18): without it, SchGen has to guess symbol_lib
        # on its own and can guess a real-sounding but wrong one (e.g.
        # "LCD" instead of the actual "Display_Character" for
        # LCD-016N002L), causing a real FileNotFoundError at build time.
        # schgen_compatible_kg_store.py already computes this exact mapping
        # for exactly this purpose - use it instead of leaving it unsaid.
        symbol_lib = kg_store.symbol_lib_for(part_id) if hasattr(kg_store, "symbol_lib_for") else None
        lib_hint = f", in the KiCad library \"{symbol_lib}\"" if symbol_lib else ""

        # Include the real pin list explicitly - confirmed necessary
        # (2026-09-22, T013): a candidate's OWN grounded part still gets
        # its pins hallucinated whenever the candidate's nets don't happen
        # to cover a pin SchGen decides it needs (e.g. wiring up a CAN
        # transceiver's TX pin when Layer 1 only grounded the part itself,
        # not that specific connection) - the model then guesses a
        # plausible-sounding name ("DATAOUT" for the real "TXD", "EN" for
        # a pin that doesn't exist on that specific part, "PA0" using a
        # different chip's naming convention). The real pin table already
        # sits in the KG, already used for the connections Layer 1 DID
        # ground (see conn_phrases below) - just not surfaced for the
        # rest. Same fix shape as the library-name fix above: give SchGen
        # the real fact instead of making it guess. Pins literally named
        # "~" (generic/unnamed, e.g. many optocoupler/passive symbols)
        # are shown by number only, since "~" itself isn't a usable name.
        # Confirmed necessary (2026-09-22, T013): enumerating every pin of a
        # large IC (tested: a real 40-pin MCU) measurably lengthens the
        # prompt enough to push our own already-tight ~31GB/32GB peak GPU
        # usage into a genuine, reproducible (2/2) CUDA OOM - not
        # fragmentation (PYTORCH_CUDA_ALLOC_CONF doesn't help; the
        # reserved-but-unallocated figure was tiny, this is real
        # exhaustion). Every candidate actually fixed by this pin data had
        # <=9 pins; large multi-pin parts weren't failing on pin-name
        # hallucination in the first place (their real failure mode, if
        # any, was elsewhere and unaffected by omitting this). Cap rather
        # than enumerate unconditionally - the memory cost is real and
        # confirmed, the benefit for large parts isn't.
        MAX_PINS_TO_ENUMERATE = 24
        pins = component.get("pins") or []
        if len(pins) > MAX_PINS_TO_ENUMERATE:
            pins = []
        pin_bits = []
        for p in pins:
            num, name, pdesc = p.get("num"), p.get("name", ""), p.get("description", "")
            # Confirmed necessary (2026-09-22, T013): giving only the
            # description for an unnamed pin ("pin 2 [LED Cathode]") isn't
            # enough - the model extracted "C" (for Cathode) out of the
            # description text as if it were the real name, rather than
            # using the pin number. Spell out explicitly that the number
            # IS the identifier to use when there's no real name.
            label = f'pin {num} ("{name}")' if name and name != "~" else f'pin number {num} (it has no name, use the number)'
            pin_bits.append(f"{label} [{pdesc}]" if pdesc else label)
        pin_hint = f"; its real pins are {', '.join(pin_bits)}" if pin_bits else ""

        desc = f"a {part_id}{lib_hint} ({note}){pin_hint}" if note else f"a {part_id}{lib_hint}{pin_hint}"
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
