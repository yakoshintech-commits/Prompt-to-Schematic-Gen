"""
Test retrieval against varied VAGUE prompts (Layer 1's actual target input -
not the detailed spec-heavy prompts used for SchGen testing). Prints top-5
retrieved ids per prompt for manual relevance inspection, per T001 Step 1.
"""

import sys

sys.path.insert(0, "/scratch/k2983/PCBSchemaGen_v2")

from kg_open_schematics_store import OpenSchematicsKGStore
from retrieval import retrieve_relevant_components

BASE_DIR = "/scratch/k2983/PCBSchemaGen_v2"
kg = OpenSchematicsKGStore(base_dir=BASE_DIR)
print(f"Loaded {len(kg.kg_component_map)} components from the 241-set.\n")

vague_prompts = [
    "I need something to blink an LED",
    "add a way to measure current",
    "I want to connect two boards together with a cable",
    "something for charging a phone over USB",
]

for prompt in vague_prompts:
    results = retrieve_relevant_components(prompt, kg, top_k=5)
    print(f"Prompt: {prompt!r}")
    if not results:
        print("  (no matches)")
    for comp in results:
        print(f"  {comp['id']!r} - category={comp.get('category')!r} subcategory={comp.get('subcategory')!r} note={comp.get('note')!r}")
    print()
