import sys, json, time
from pathlib import Path
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/layer1")

from kg_open_schematics_store import OpenSchematicsKGStore
from schgen_compatible_kg_store import SchGenCompatibleKGStore
from pipeline import run_layer1
from schgen_bridge import candidate_to_detailed_prompt

base_kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
kg = SchGenCompatibleKGStore(base_kg)

items = sorted(kg.kg_component_map.items(), key=lambda kv: kv[0])
print(f"total rows: {len(items)}")

results = []
t_start = time.time()
for i, (part_id, comp) in enumerate(items):
    note = comp.get("note", "").strip()
    category = comp.get("category", "")
    subcategory = comp.get("subcategory", "")
    prompt = f"I need to build a circuit that uses: {note}." if note else \
             f"I need to build a circuit that uses a {subcategory.replace('_', ' ')} ({part_id})."

    t0 = time.time()
    try:
        result = run_layer1(prompt, kg, n=1, max_attempts=3)
        candidate = result["ranked"][0]
        status = candidate.get("verification_status")
        parts = [c["part_id"] for c in candidate.get("components", [])]
        errors = candidate.get("verification_errors")
        entry = {
            "idx": i, "part_id": part_id, "category": category, "subcategory": subcategory,
            "note": note, "prompt": prompt, "status": status,
            "attempts": candidate.get("_attempts"), "components": parts,
            "errors": errors, "elapsed_s": round(time.time() - t0, 1),
        }
        if status == "passed":
            entry["detailed_prompt"] = candidate_to_detailed_prompt(candidate, kg)
            entry["candidate"] = candidate
    except Exception as e:
        entry = {
            "idx": i, "part_id": part_id, "category": category, "subcategory": subcategory,
            "note": note, "prompt": prompt, "status": "exception", "error_text": str(e),
            "elapsed_s": round(time.time() - t0, 1),
        }

    results.append(entry)
    elapsed_total = time.time() - t_start
    print(f"[{i+1}/{len(items)}] {part_id} ({category}/{subcategory}): {entry['status']} "
          f"({entry['elapsed_s']}s, total {elapsed_total/60:.1f}m)", flush=True)

    with open(_HERE / "t013_full_layer1_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

print()
print("=" * 70)
print("SUMMARY")
from collections import Counter
status_counts = Counter(r["status"] for r in results)
for status, count in status_counts.most_common():
    print(f"  {status}: {count}/{len(results)}")
print(f"total elapsed: {(time.time() - t_start)/60:.1f} minutes")
