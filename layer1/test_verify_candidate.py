"""
Test verify_candidate against 3 synthetic candidates per T001 Step 4:
one with a hallucinated part (should be rejected WITHOUT calling the real
verifier), one real but incompletely wired (should trip a real constraint
check), one fully correct (should pass). Shows real verifier output, not
a paraphrase.
"""

import sys

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
from kg_open_schematics_store import OpenSchematicsKGStore
import verify_candidate as vc_module
from verify_candidate import verify_candidate

kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")

# --- Candidate 1: hallucinated part - should be rejected, verifier never called ---
hallucinated_candidate = {
    "id": "bad_part",
    "components": [{"ref": "U1", "part_id": "FAKE_IC_999"}],
    "nets": [],
}

# --- Candidate 2: real component (AMC1350), incompletely wired - trips a real constraint ---
# AMC1350 has supply_pair (VDD1/GND1, VDD2/GND2) and must_be_connected (INP/INN)
# constraints - confirmed in Step 0. Real pin numbers looked up from kg_store
# (not guessed - an earlier draft of this test guessed wrong numbers, which
# got rejected by Step 3's fact-check before ever reaching the real verifier,
# not testing what this case is meant to test). Deliberately omit VDD1/VDD2/
# GND2 to trip real supply_missing checks while still passing fact-checking.
amc1350_pins = {p["name"]: str(p["num"]) for p in kg.get_component("AMC1350")["pins"]}
print("Real AMC1350 pins:", amc1350_pins, "\n")

incomplete_candidate = {
    "id": "incomplete_amc1350",
    "components": [{"ref": "U1", "part_id": "AMC1350"}],
    "nets": [
        {"name": "GND1_NET", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["GND1"], "pin_name": "GND1"}]},
        {"name": "SIG_P", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["INP"], "pin_name": "INP"}]},
        {"name": "SIG_N", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["INN"], "pin_name": "INN"}]},
        # VDD1, VDD2, GND2 deliberately left unconnected
    ],
}

# --- Candidate 3: fully correct - every constraint satisfied ---

complete_candidate = {
    "id": "complete_amc1350",
    "components": [{"ref": "U1", "part_id": "AMC1350"}],
    "nets": [
        {"name": "VDD1_NET", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["VDD1"], "pin_name": "VDD1"}]},
        {"name": "GND1_NET", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["GND1"], "pin_name": "GND1"}]},
        {"name": "VDD2_NET", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["VDD2"], "pin_name": "VDD2"}]},
        {"name": "GND2_NET", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["GND2"], "pin_name": "GND2"}]},
        {"name": "SIG_P", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["INP"], "pin_name": "INP"}]},
        {"name": "SIG_N", "endpoints": [{"ref": "U1", "pin_id": amc1350_pins["INN"], "pin_name": "INN"}]},
    ],
}

# Track real-verifier calls to PROVE candidate 1 never reaches it, not just assert it by reading code.
call_count = {"n": 0}
_real_validate_complex_task = vc_module.validate_complex_task


def _counting_validate_complex_task(*args, **kwargs):
    call_count["n"] += 1
    return _real_validate_complex_task(*args, **kwargs)


vc_module.validate_complex_task = _counting_validate_complex_task

for label, candidate in [
    ("1. Hallucinated part (expect: rejected, verifier NOT called)", hallucinated_candidate),
    ("2. Real component, incompletely wired (expect: failed_checks)", incomplete_candidate),
    ("3. Fully correct (expect: passed)", complete_candidate),
]:
    calls_before = call_count["n"]
    result = verify_candidate(candidate, kg)
    calls_after = call_count["n"]
    print(f"{label}")
    print(f"  verification_status: {result['verification_status']}")
    print(f"  real verifier called this time: {calls_after > calls_before}")
    print(f"  errors:")
    for e in result["verification_errors"]:
        print(f"    - {e}")
    print(f"  warnings:")
    for w in result["verification_warnings"]:
        print(f"    - {w}")
    print()
