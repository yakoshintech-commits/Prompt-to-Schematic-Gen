"""
End-to-end test of generate_candidates: real retrieval -> real LLM call ->
real parsed candidates. Prints full output for inspection, per T001's
"show real output before proceeding" instruction.
"""

import json
import sys

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
from kg_open_schematics_store import OpenSchematicsKGStore
from generate_candidates import generate_candidates

kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")

vague_prompt = "I need something to blink an LED"
candidates = generate_candidates(vague_prompt, kg, n=2)

print(f"Got {len(candidates)} candidate(s) for {vague_prompt!r}:\n")
for c in candidates:
    print(json.dumps(c, indent=2))
    print()
