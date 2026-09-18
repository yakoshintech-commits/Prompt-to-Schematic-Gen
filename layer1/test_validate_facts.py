"""
Test validate_parts_exist against 3 hand-built synthetic candidates, per
T001 Step 3: one fully grounded, one with a hallucinated part_id, one with
a hallucinated pin. Prints real output for both failure modes.
"""

import sys

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
from kg_open_schematics_store import OpenSchematicsKGStore
from validate_facts import validate_parts_exist

kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")

# Real pins on R: [{"num":1,"name":"~"}, {"num":2,"name":"~"}]
# Real pins on LED: confirmed earlier as A (anode)/K (cathode)
led_pins = kg.get_component("LED")["pins"]
print("Real LED pins (for reference):", led_pins, "\n")

grounded_candidate = {
    "id": "grounded",
    "components": [
        {"ref": "R1", "part_id": "R"},
        {"ref": "D1", "part_id": "LED"},
    ],
    "nets": [
        {"name": "VCC", "endpoints": [
            {"ref": "R1", "pin_id": "1", "pin_name": "~"},
        ]},
        {"name": "MID", "endpoints": [
            {"ref": "R1", "pin_id": "2", "pin_name": "~"},
            {"ref": "D1", "pin_id": str(led_pins[0]["num"]), "pin_name": led_pins[0]["name"]},
        ]},
    ],
}

hallucinated_part_candidate = {
    "id": "bad_part",
    "components": [
        {"ref": "R1", "part_id": "R"},
        {"ref": "U1", "part_id": "IC1"},  # does not exist anywhere in the KG
    ],
    "nets": [
        {"name": "VCC", "endpoints": [
            {"ref": "R1", "pin_id": "1", "pin_name": "~"},
            {"ref": "U1", "pin_id": "1", "pin_name": "VDD"},
        ]},
    ],
}

hallucinated_pin_candidate = {
    "id": "bad_pin",
    "components": [
        {"ref": "D1", "part_id": "LED"},
    ],
    "nets": [
        {"name": "VCC", "endpoints": [
            # LED is a real 2-pin part; pin 99 does not exist on it
            {"ref": "D1", "pin_id": "99", "pin_name": "FAKE_PIN"},
        ]},
    ],
}

for label, candidate in [
    ("1. Fully grounded (expect PASS)", grounded_candidate),
    ("2. Hallucinated part_id (expect FAIL)", hallucinated_part_candidate),
    ("3. Hallucinated pin (expect FAIL)", hallucinated_pin_candidate),
]:
    passed, reason = validate_parts_exist(candidate, kg)
    print(f"{label}")
    print(f"  passed={passed}")
    print(f"  reason={reason!r}")
    print()
