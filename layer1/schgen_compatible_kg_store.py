"""
SchGenCompatibleKGStore: wraps an existing kg_store (OpenSchematicsKGStore or
KGStore) and restricts it to the subset of components that actually exist as
exact-name symbols in SchGen's own KiCad symbol library
(/usr/share/kicad/symbols/*.kicad_sym, per SchGen/config.py's
KICAD_SYMBOL_LIB_PATH on Linux).

Built after confirming empirically (2026-09-18) that only 133 of the
241-component open-schematics KG's parts (55%) have an exact-name match in
SchGen's stock library - the rest (TP4056, SSD1306, 0402LED, etc.) don't
exist there under that name. Feeding a Layer 1 candidate that references a
part SchGen can't find would force SchGen to substitute something else on
its own judgment, silently reintroducing the exact ungrounded-guessing
problem Layer 1 exists to prevent, just one layer downstream. Intersecting
the vocabulary BEFORE generation (here) means anything Layer 1 verifies is
guaranteed placeable in SchGen - the fix belongs at the source, not as a
correction after the fact.

kicad_symbol_overlap.json (built once by parsing every real .kicad_sym
library file with sexpdata and recording each file's actual top-level
(symbol "NAME" ...) definitions - see tools/rebuild_kicad_symbol_overlap.py)
maps part_id -> [kicad_sym library filename(s) that define it as a real
top-level symbol]. An earlier version was built with a grep over each
file's raw text, which matched the substring anywhere (pin names, property
values, keywords, even other symbols' sub-unit names) instead of a real
top-level part - that produced long, mostly-wrong candidate lists for
short generic IDs like "R"/"C"/"L" (T009, found and fixed 2026-09-22:
rebuilding with a real s-expression walk collapsed all but one of the 133
known part_ids down to a single, correct library - the sole remaining
multi-entry case, "D", is a genuine same-name collision between two real
libraries, not a bug; symbol_lib_for() below prefers Device for that case).
"""

import json
import os

KICAD_SYMBOL_LIB_PATH = "/usr/share/kicad/symbols"


def _normalize_part_id(part_id):
    if not part_id:
        return ""
    return str(part_id).strip()


class SchGenCompatibleKGStore:
    """Duck-typed, same interface as KGStore/OpenSchematicsKGStore, restricted
    to components with a real symbol in SchGen's own KiCad library."""

    def __init__(self, base_kg_store, overlap_path=None):
        if overlap_path is None:
            overlap_path = os.path.join(os.path.dirname(__file__), "kicad_symbol_overlap.json")
        with open(overlap_path, "r") as f:
            self.symbol_map = json.load(f)  # part_id -> [kicad_sym lib filename(s)]

        allowed = set(self.symbol_map.keys())
        self.component_map = {k: v for k, v in base_kg_store.component_map.items() if k in allowed}
        self.kg_component_map = {k: v for k, v in base_kg_store.kg_component_map.items() if k in allowed}

    def get_component(self, part_id):
        return self.kg_component_map.get(_normalize_part_id(part_id))

    def get_component_info(self, part_id):
        return self.component_map.get(_normalize_part_id(part_id))

    def get_category(self, part_id):
        comp = self.get_component(part_id)
        if comp and comp.get("category"):
            return comp.get("category")
        comp_info = self.get_component_info(part_id)
        if comp_info and comp_info.get("category"):
            return comp_info.get("category")
        return None

    def get_pin_roles(self, part_id):
        comp = self.get_component(part_id)
        if comp and comp.get("pin_roles"):
            return comp.get("pin_roles")
        return {}

    def get_constraints(self, part_id):
        comp = self.get_component(part_id)
        if comp and comp.get("generic_constraints"):
            return comp.get("generic_constraints")
        return []

    def has_component(self, part_id):
        part_id = _normalize_part_id(part_id)
        return part_id in self.component_map or part_id in self.kg_component_map

    def symbol_lib_for(self, part_id):
        """SchGen-specific: which stock KiCad library file actually contains
        this part_id's symbol. kicad_symbol_overlap.json now maps to real,
        exact top-level symbol names only (parsed via sexpdata - see
        rebuild instructions in that file's own comment), so a part_id with
        more than one candidate means it's a genuine same-name collision
        across two real libraries, not a grep false-positive. The only
        observed case (2026-09-22) is "D", which exists as a real top-level
        symbol in both Device.kicad_sym and Simulation_SPICE.kicad_sym.
        Prefer Device when present - it's KiCad's canonical library for
        exactly these generic single/double-letter parts (R, C, L, D,
        LED...) - rather than relying on whatever order the list happens
        to be in."""
        libs = self.symbol_map.get(_normalize_part_id(part_id))
        if not libs:
            return None
        if "Device" in libs:
            return "Device"
        return libs[0]

    def real_pins_for(self, part_id):
        """Pin (number, name) pairs read directly from the real .kicad_sym
        file for this part_id's symbol - NOT the KG's own `pins[].name`
        field. Found necessary (2026-09-22, T013): the KG's pin names are
        datasheet-style ("TRIG", "OUT", "RESET"...) and don't always match
        the specific stock KiCad symbol's own (often more abbreviated -
        "TR", "Q", "R"...) pin names - confirmed for NE555D, where trusting
        the KG's names regressed a previously-passing candidate (the model's
        own trained knowledge of the real KiCad symbol was more accurate
        than the mismatched "ground truth" we were handing it). The actual
        .kicad_sym file SchGen builds against is the only real ground truth
        for what name it needs - use that directly instead of a second-hand
        copy that can drift from it. Returns [] if the symbol can't be
        found or parsed (caller should treat that as "no pin data available",
        not as an error - same safe fallback as before this existed)."""
        part_id = _normalize_part_id(part_id)
        lib = self.symbol_lib_for(part_id)
        if not lib:
            return []
        try:
            import sexpdata
        except ImportError:
            return []
        path = os.path.join(KICAD_SYMBOL_LIB_PATH, f"{lib}.kicad_sym")
        try:
            with open(path, "r", encoding="utf-8") as f:
                parsed = sexpdata.loads(f.read())
        except (OSError, Exception):
            return []

        def _find_top_level(sexp, name):
            for child in sexp:
                if (isinstance(child, list) and len(child) >= 2
                        and isinstance(child[0], sexpdata.Symbol)
                        and child[0].value() == "symbol"
                        and child[1] == name):
                    return child
            return None

        symbol = _find_top_level(parsed, part_id)
        if symbol is None:
            return []
        # Resolve `extends` (many parts share a base symbol's pin/unit
        # graphics - see T014) by reading pins from the base instead.
        for item in symbol:
            if (isinstance(item, list) and item and isinstance(item[0], sexpdata.Symbol)
                    and item[0].value() == "extends"):
                symbol = _find_top_level(parsed, item[1]) or symbol
                break

        pins = []
        for unit in symbol:
            if not (isinstance(unit, list) and len(unit) > 2
                    and isinstance(unit[0], sexpdata.Symbol) and unit[0].value() == "symbol"):
                continue
            for pin_form in unit[2:]:
                if not (isinstance(pin_form, list) and pin_form
                        and isinstance(pin_form[0], sexpdata.Symbol) and pin_form[0].value() == "pin"):
                    continue
                num, name = None, None
                for f in pin_form:
                    if isinstance(f, list) and f and isinstance(f[0], sexpdata.Symbol):
                        if f[0].value() == "number":
                            num = f[1]
                        elif f[0].value() == "name":
                            name = f[1]
                if num is not None:
                    pins.append((num, name or "~"))
        return pins
