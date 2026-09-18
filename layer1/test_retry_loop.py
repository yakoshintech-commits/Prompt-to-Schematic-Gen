"""
Test the new verify-and-retry loop for real: does actually feeding the real
error back get us to a genuine PASS, where every one-shot generation this
session failed?
"""

import json
import sys

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
from kg_open_schematics_store import OpenSchematicsKGStore
from pipeline import run_layer1

kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")

result = run_layer1("I need something to blink an LED", kg, n=1, max_attempts=3)

for c in result["candidates"]:
    print(f"id={c.get('id')!r} status={c.get('verification_status')!r} attempts={c.get('_attempts')} score={c.get('score'):.3f}")
    if c.get("verification_errors"):
        print(f"  final errors: {c['verification_errors']}")
    print()
    print(json.dumps(c, indent=2))
