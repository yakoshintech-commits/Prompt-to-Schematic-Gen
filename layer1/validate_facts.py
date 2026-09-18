"""
Hard hallucination filter: deterministic, no LLM. Checks every part_id
referenced in a candidate exists in kg_store, and every pin_id/pin_name
referenced in its nets exists on that SPECIFIC component's real pin list.
Runs before the real verifier (Step 4), so a candidate that's already known
to reference a fabricated part or pin never wastes a verifier call. Per
T001 Step 3.

Confirmed necessary, not theoretical: see skills/layer1-pipeline/SKILL.md's
"Step 2 generation still hallucinates" finding - a real generate_candidates()
run invented part_ids not in the vocabulary and got a real component's pin
mapping wrong (claimed pin 2 = "VSS" on SK6812, real pin 2 is "DIN").
"""


def validate_parts_exist(candidate: dict, kg_store) -> tuple[bool, str]:
    """
    Returns (True, "") if every part_id and every net endpoint's (pin_id,
    pin_name) pair is real, per kg_store. Returns (False, reason) on the
    FIRST mismatch found - this is a fast fail-fast check, not a full report;
    the real verifier's errors (Step 4) are where a full report belongs.
    """
    ref_to_part_id = {}

    for comp in candidate.get("components", []):
        ref = comp.get("ref")
        part_id = comp.get("part_id")
        if not kg_store.has_component(part_id):
            return False, f"Component {ref!r} references part_id {part_id!r}, which does not exist in the knowledge graph."
        ref_to_part_id[ref] = part_id

    for net in candidate.get("nets", []):
        net_name = net.get("name")
        for ep in net.get("endpoints", []):
            ref = ep.get("ref")
            pin_id = str(ep.get("pin_id"))
            pin_name = str(ep.get("pin_name"))

            if ref not in ref_to_part_id:
                return False, f"Net {net_name!r} references component {ref!r}, which is not in this candidate's components list."

            part_id = ref_to_part_id[ref]
            real_component = kg_store.get_component(part_id)
            real_pins = real_component.get("pins", []) if real_component else []
            real_pin_pairs = {(str(p.get("num")), str(p.get("name"))) for p in real_pins}

            if (pin_id, pin_name) not in real_pin_pairs:
                available = sorted(real_pin_pairs)
                return False, (
                    f"Net {net_name!r} references pin (pin_id={pin_id!r}, pin_name={pin_name!r}) "
                    f"on component {ref!r} (part_id={part_id!r}), but that part's real pins are {available}. "
                    f"This pin_id/pin_name pair does not exist on this specific component."
                )

    return True, ""
