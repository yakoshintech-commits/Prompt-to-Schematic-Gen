"""
Wires in PCBSchemaGen_v2's real deterministic verifier. Per T001 Step 4.

build_snapshot follows the exact snapshot shape confirmed empirically in
skills/pcbschemagen-verifier/SKILL.md (Step 0) - not re-derived here, and
not trusting any README pseudocode. Key point from that investigation:
each component's "pins" list must be its FULL real pin list (not just
pins referenced in nets), since augment_snapshot() sets pin_role per
declared pin - so build_snapshot looks that up from kg_store, since
Layer 1's own candidate schema doesn't carry a full pin list per component.

verify_candidate runs validate_parts_exist (Step 3) FIRST and exits early
to "rejected" on failure - a candidate already known to reference a
fabricated part/pin never reaches the real verifier, per the task spec.
"""

import sys

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
from framework.topo import validate_complex_task
from framework.topo.build_topology import augment_snapshot

from validate_facts import validate_parts_exist


def build_snapshot(candidate: dict, kg_store) -> dict:
    components = []
    for comp in candidate.get("components", []):
        part_id = comp["part_id"]
        ref = comp["ref"]
        real_component = kg_store.get_component(part_id)
        real_pins = real_component.get("pins", []) if real_component else []
        pins = [{"pin_id": str(p.get("num")), "pin_name": str(p.get("name"))} for p in real_pins]
        components.append({"part_id": part_id, "ref": ref, "pins": pins})

    nets = []
    for net in candidate.get("nets", []):
        endpoints = [
            {"ref": ep["ref"], "pin_id": str(ep["pin_id"]), "pin_name": str(ep["pin_name"])}
            for ep in net.get("endpoints", [])
        ]
        nets.append({"name": net["name"], "endpoints": endpoints})

    # Cross-reference nets back into each component's own pin dicts. This is
    # NOT done by augment_snapshot (confirmed - it only sets pin_role and
    # category) but is required: _check_constraints's _is_connected() reads
    # pin_info.get("net") directly off each component's pin, not from the
    # separate top-level nets list. Confirmed empirically - omitting this
    # made every pin report as "missing net" even when correctly wired in
    # the nets list, before this fix was added.
    comp_by_ref = {c["ref"]: c for c in components}
    for net in nets:
        for ep in net["endpoints"]:
            comp = comp_by_ref.get(ep["ref"])
            if not comp:
                continue
            for pin in comp["pins"]:
                if pin["pin_id"] == ep["pin_id"] and pin["pin_name"] == ep["pin_name"]:
                    pin["net"] = net["name"]

    return {"components": components, "nets": nets}


def verify_candidate(candidate: dict, kg_store) -> dict:
    """
    Mutates and returns candidate with verification_status set to one of
    "passed", "failed_checks", or "rejected", plus verification_errors and
    verification_warnings (lists of human-readable strings).
    """
    facts_ok, reason = validate_parts_exist(candidate, kg_store)
    if not facts_ok:
        candidate["verification_status"] = "rejected"
        candidate["verification_errors"] = [reason]
        candidate["verification_warnings"] = []
        return candidate

    snapshot = build_snapshot(candidate, kg_store)
    snapshot = augment_snapshot(snapshot, kg_store)

    # task_id=None: this candidate doesn't correspond to any specific
    # PCBSchemaGen_v2 benchmark task - confirmed correct in Step 0's live
    # test (core constraint checks still run; only benchmark-task-specific
    # extra checks are skipped, which is right since there's no such task here).
    passed, errors, warnings = validate_complex_task(snapshot, task_id=None, kg_store=kg_store)

    candidate["verification_status"] = "passed" if passed else "failed_checks"
    candidate["verification_errors"] = [str(e) for e in errors]
    candidate["verification_warnings"] = [str(w) for w in warnings]
    return candidate
