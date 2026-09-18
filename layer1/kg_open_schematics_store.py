"""
OpenSchematicsKGStore: a standalone, duck-typed drop-in for PCBSchemaGen_v2's
KGStore, loading the 241-component "Open Schematics" set instead of the
default 48. Does not modify PCBSchemaGen_v2's own code.

KGStore (framework/topo/kg_loader.py) is hardcoded to load component.json +
kg_component.json from base_dir - confirmed by reading _load_all(), which
builds those two exact filenames with no override parameter. kg_open_schematics.json
is not wired in anywhere in PCBSchemaGen_v2's own code.

kg_open_schematics.json has the identical schema to kg_component.json
(top-level pin_roles_vocab + components keys, each component carrying
pin_roles/generic_constraints/subcategory already) - confirmed by direct
comparison, so this class can point both of KGStore's two internal maps at
the one file, rather than replicating the two-file merge KGStore does.
"""

import json
import os


def _normalize_part_id(part_id):
    if not part_id:
        return ""
    return str(part_id).strip()


class OpenSchematicsKGStore:
    """Mirrors KGStore's exact public interface, sourced from the 241-component set."""

    def __init__(self, base_dir="."):
        self.base_dir = base_dir
        self.component_map = {}
        self.kg_component_map = {}
        self._load_all()

    def _load_all(self):
        path = os.path.join(self.base_dir, "kg", "kg_open_schematics.json")
        with open(path, "r") as f:
            data = json.load(f)
        components = {c["id"]: c for c in data.get("components", [])}
        # kg_open_schematics.json already carries every field kg_component.json's
        # map has (pin_roles, generic_constraints, subcategory) plus the base
        # fields component.json's map has - one file covers both KGStore maps.
        self.component_map = components
        self.kg_component_map = components

    def get_component(self, part_id):
        part_id = _normalize_part_id(part_id)
        return self.kg_component_map.get(part_id)

    def get_component_info(self, part_id):
        part_id = _normalize_part_id(part_id)
        return self.component_map.get(part_id)

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
