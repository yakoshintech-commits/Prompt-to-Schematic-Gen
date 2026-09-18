"""
End-to-end test of run_layer1 (Step 5): generate -> verify -> score -> rank,
on a real vague prompt. Shows real output, per T001's own instructions.
"""

import json
import sys

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
from kg_open_schematics_store import OpenSchematicsKGStore
from pipeline import run_layer1

kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")

result = run_layer1("I need something to blink an LED", kg, n=3)

print(f"Total candidates: {len(result['candidates'])}\n")
print("=== Ranked order ===")
for i, c in enumerate(result["ranked"], 1):
    print(f"{i}. id={c.get('id')!r} status={c.get('verification_status')!r} score={c.get('score'):.3f} n_components={len(c.get('components', []))}")
    if c.get("verification_errors"):
        print(f"   errors: {c['verification_errors']}")

print("\n=== Full first-ranked candidate ===")
print(json.dumps(result["ranked"][0], indent=2))
