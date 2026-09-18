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

kicad_symbol_overlap.json (built once via a real grep over the stock
library, not assumed) maps part_id -> [kicad_sym library filename(s) that
contain it].
"""

import json
import os


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
        """SchGen-specific: which stock KiCad library file(s) actually contain
        this part_id's symbol. Returns the first match, or None."""
        libs = self.symbol_map.get(_normalize_part_id(part_id))
        return libs[0] if libs else None
