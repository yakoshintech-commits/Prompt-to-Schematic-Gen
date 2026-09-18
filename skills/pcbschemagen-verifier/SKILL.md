# PCBSchemaGen_v2 Verifier

## Purpose

How to load real component data and run PCBSchemaGen_v2's deterministic verifier against a Layer 1 candidate, without re-discovering its interface, snapshot shape, or gotchas from scratch each time.

## Key facts (confirmed empirically, not assumed)

All facts below confirmed by reading `/scratch/k2983/PCBSchemaGen_v2`'s actual source and running a live minimal test (2026-09-18), not by trusting any README pseudocode.

**KGStore's real public interface** (`framework/topo/kg_loader.py`):
```python
KGStore(base_dir=".")                    # loads component.json + kg_component.json from base_dir
.get_component(part_id) -> dict | None   # from kg_component.json (has pin_roles, generic_constraints, subcategory)
.get_component_info(part_id) -> dict | None  # from component.json (base fields only - id/category/footprint/note/pins)
.get_category(part_id) -> str | None     # tries get_component first, falls back to get_component_info
.get_pin_roles(part_id) -> dict          # {pin_name_or_num: role_string}, {} if none
.get_constraints(part_id) -> list        # list of constraint dicts, [] if none
.has_component(part_id) -> bool          # checks both maps
infer_category(part_id, ref=None, kg_store=None) -> str  # module-level function, has ref-prefix fallback heuristics
```

**component.json vs kg_component.json - corrects an earlier wrong assumption**: these are NOT a "48 vs 241" split. Both describe the **same 48 components** - `kg_component.json` is a strict superset of `component.json`'s fields (adds `pin_roles`, `generic_constraints`, `subcategory` on top of `id`/`category`/`footprint`/`note`/`pins`). The real 241-component set is a **separate file**, `kg/kg_open_schematics.json`, with the **identical schema** to `kg_component.json` (`pin_roles_vocab` + `components` keys) - confirmed field-for-field identical for a shared component (`R`). This means `OpenSchematicsKGStore` doesn't need to replicate `KGStore`'s two-file-merge logic - it can just point both `component_map` and `kg_component_map` at the one 241-entry file, since that file already carries every field `component.json` has plus more.

**Snapshot shape** (confirmed via `build_topology.py` + a live test):
```python
snapshot = {
    "components": [
        {"part_id": str, "ref": str, "pins": [{"pin_id": str, "pin_name": str}, ...]},
        # augment_snapshot() adds "category" and each pin's "pin_role" in place
    ],
    "nets": [
        {"name": str, "endpoints": [{"ref": str, "pin_id": str, "pin_name": str}, ...]},
        # augment_snapshot() adds each endpoint's "pin_role" and "component_category" in place
    ],
}
```
`index_snapshot(snapshot)` is a separate, simpler transform: returns `{"components": {ref: comp}, "nets": {name: net}}` for O(1) lookup - used internally by the checkers, not something Layer 1 needs to call directly before verifying.

**Pin-role vocabulary**: exactly 32 named roles, defined in `kg_component.json`'s (and `kg_open_schematics.json`'s) top-level `pin_roles_vocab` dict. Confirmed list: `supply_vdd, supply_gnd, primary_vdd, primary_gnd, secondary_vdd, secondary_gnd, sense_plus, sense_minus, out, out_plus, out_minus, logic_in, logic_out, passive_terminal (symmetric), diode_anode, diode_cathode, buck_vin, buck_gnd, buck_sw, buck_fb, buck_en, buck_boot, halfbridge_hb, halfbridge_hs, gate_ho, gate_lo, mosfet_gate, mosfet_drain, mosfet_source, mosfet_kelvin_source, xfmr_primary, xfmr_secondary`.

**The 4 constraint predicate types**, real field shapes (from actual `generic_constraints` entries, not the paper's description):
```python
{"type": "supply_pair", "vdd_pin": "VDD1", "gnd_pin": "GND1"}
{"type": "must_be_connected", "pins": ["INP", "INN"]}
{"type": "differential_pair_must_be_distinct", "pins": ["+IN", "-IN"]}
{"type": "driving_pair", "gate_pin": "4", "source_pin": "1"}
```

**`augment_snapshot` is NOT re-exported from `framework/topo/__init__.py`** - confirmed by an actual `ImportError` when tried. `__init__.py` re-exports `index_snapshot` from the same module (`build_topology.py`) but not `augment_snapshot`. Needs a direct submodule import:
```python
from framework.topo import KGStore, validate_complex_task, format_validation_report, get_validation_feedback_for_llm
from framework.topo.build_topology import augment_snapshot  # NOT in the package __init__
```

**`validate_complex_task(snapshot, task_id, kg_store)` is not a general-purpose verifier by default** - `task_id` refers to PCBSchemaGen_v2's own benchmark numbering (`COMPLEX_POWER_TASKS = range(17,24)`, `COMPLEX_UNIVERSAL_TASKS = {49,50,51,52,54,55,62,64,65,66,67,68}` in `task_config_loader.py`), and most of its checks (`tps54302_diode`, `strict_halfbridge`, `ks_source_rlc`, `ucc5390e_vin_minus`, `ucc27511_output`) are gated behind `if task_id and tcfg.has_check(task_id, "...")`. **Confirmed by a live test**: passing `task_id=None` is fine for a Layer 1 candidate that doesn't correspond to any specific benchmark task - the core, always-on checks still run (per-component `generic_constraints` via `_check_constraints`, plus two hardcoded part-specific checks), and it correctly returns `(True, [], [])` for a valid trivial circuit. The task-specific extra checks are just skipped, which is correct since a Layer 1 candidate has no PCBSchemaGen task_id to give it.

**Real error shape**: `validate_complex_task` returns `(passed: bool, errors: list[VerificationError], warnings: list[VerificationError])`. `VerificationError` fields confirmed via a live constraint-violation test: `phase, severity, category, message, component, pin, net, constraint, suggestion, recurrent`. The `suggestion` field is already actionable, human-readable guidance (e.g. `"Connect supply pin VDD1 on U1 to the power rail."`) - this is exactly the kind of specific feedback that mattered for SchGen's own verify-and-retry loop (see the schgen-integration skill's near-miss-symbol lesson). `get_validation_feedback_for_llm(errors, warnings)` formats these into retry-ready markdown text already.

**No `isinstance` checks anywhere in `framework/`** against `KGStore` - confirmed via `grep -rn "isinstance.*KGStore" framework/` returning nothing. Safe as a duck-typed drop-in for `OpenSchematicsKGStore`.

## Using the 241-component KG instead of the default 48

`KGStore` is hardcoded (`framework/topo/kg_loader.py`'s `_load_all`) to load `component.json` + `kg_component.json` from `base_dir`, with no parameter to point it at a different file - `kg/kg_open_schematics.json` (241 components) is not wired in anywhere in PCBSchemaGen_v2's own code.

`layer1/kg_open_schematics_store.py`'s `OpenSchematicsKGStore` mirrors `KGStore`'s exact public interface (same method names, signatures, return shapes) but loads from that one 241-entry file instead - safe as a standalone parallel implementation since `kg_open_schematics.json` already has the identical schema to `kg_component.json` (both maps can point at the same loaded dict, no two-file merge needed).

**Proven via `layer1/test_kg_open_schematics_store.py`** (real output, not asserted blind):
- A shared component (`R`, in both the 48-set and the 241-set) returns byte-identical results from both classes.
- A 241-set-only component (`0402LED`) returns `None`/`False` from `KGStore` and a real, fully-populated component dict from `OpenSchematicsKGStore` - confirms genuine wider coverage, not a silent fallback to the same 48 parts under a different class name.
- No `isinstance(kg_store, KGStore)` checks exist anywhere in `framework/` (confirmed via `grep`), so `check_system_topology`, `validate_complex_task`, `augment_snapshot`, etc. all accept `OpenSchematicsKGStore` as a drop-in wherever they currently accept `KGStore` - they only ever call methods on it.

## Common mistakes to avoid

- Don't assume `component.json`/`kg_component.json` are a "48 vs 241" split - they're the same 48 components at different field-completeness; the real 241-set is `kg/kg_open_schematics.json`, a separate file.
- Don't import `augment_snapshot` from `framework.topo` - it'll raise `ImportError`. Import from `framework.topo.build_topology` directly.
- Don't pass a made-up `task_id` to `validate_complex_task` for a generic Layer 1 candidate - pass `None`. The function handles it correctly and still runs the general checks; a fabricated task_id could accidentally enable checks that don't apply (e.g. `strict_halfbridge`) and produce false failures.
- `must_be_connected` on a constraint's `pins` list may mean something more specific than "each pin is on *some* net" - a live test with `INP`/`INN` connected to two *different* nets still reported both as "unconnected." Confirmed the constraint fires in that case; **not yet confirmed exactly what condition satisfies it** (likely: connected to the *same* net, or to each other specifically). Investigate `_check_constraints`'s `must_be_connected` branch in `phase2_checks.py` before relying on this predicate in Layer 1's own candidate design.

## Code references

- `framework/topo/kg_loader.py` - `KGStore`, `infer_category`
- `framework/topo/build_topology.py` - `augment_snapshot` (direct import only), `index_snapshot`
- `framework/topo/complex_task_validator.py` - `validate_complex_task`, `format_validation_report`, `get_validation_feedback_for_llm`, `is_complex_task`, `get_complex_task_info`
- `framework/topo/phase2_checks.py` - `run_phase2_checks`, `_check_constraints` (the `must_be_connected` open question lives here)
- `framework/topo/task_config_loader.py` - `COMPLEX_POWER_TASKS`, `COMPLEX_UNIVERSAL_TASKS`, `has_check`
- `framework/topo/__init__.py` - authoritative list of what's actually re-exported
- `component.json`, `kg_component.json`, `kg/kg_open_schematics.json` - the three data files, schemas confirmed above
