"""
Side-by-side test: KGStore (48-component default) vs OpenSchematicsKGStore
(241-component Open Schematics set), per T001 Step 0b.

Proves:
1. Both work identically for a component that exists in the 48-set (same
   shape, same values) - confirms the drop-in interface really matches.
2. Only OpenSchematicsKGStore finds a component that exists ONLY in the
   241-set - confirms genuine wider coverage, not a silent fallback to the
   same 48 components under a different class name.
"""

import sys

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")

from framework.topo import KGStore
from kg_open_schematics_store import OpenSchematicsKGStore

BASE_DIR = "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2"

kg_default = KGStore(base_dir=BASE_DIR)
kg_open = OpenSchematicsKGStore(base_dir=BASE_DIR)

print("=== Shared component: 'R' (exists in both the 48-set and the 241-set) ===")
print("KGStore.get_component('R'):        ", kg_default.get_component("R"))
print("OpenSchematicsKGStore.get_component('R'):", kg_open.get_component("R"))
assert kg_default.get_component("R") == kg_open.get_component("R"), "shared component should match exactly"
print("MATCH: identical shape and values for a shared component.\n")

print("=== 241-set-only component: '0402LED' (not in the default 48) ===")
default_result = kg_default.get_component("0402LED")
open_result = kg_open.get_component("0402LED")
print("KGStore.get_component('0402LED'):        ", default_result)
print("OpenSchematicsKGStore.get_component('0402LED'):", open_result)
assert default_result is None, "the default 48-component KGStore should NOT have this part"
assert open_result is not None, "OpenSchematicsKGStore SHOULD have this part - proves real wider coverage"
print("CONFIRMED: OpenSchematicsKGStore finds it, default KGStore does not - genuine 241-set coverage, not a silent fallback.\n")

print("=== has_component() agreement check ===")
print("KGStore.has_component('0402LED'):        ", kg_default.has_component("0402LED"))
print("OpenSchematicsKGStore.has_component('0402LED'):", kg_open.has_component("0402LED"))

print("\nAll assertions passed.")
