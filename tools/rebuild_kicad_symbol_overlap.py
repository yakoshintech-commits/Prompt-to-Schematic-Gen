"""
Rebuild kicad_symbol_overlap.json properly: for each .kicad_sym library file,
parse it as a real s-expression and record only its TOP-LEVEL symbol names
(the direct children of the (kicad_symbol_lib ...) form that are themselves
(symbol "NAME" ...) forms). This is what the previous grep-based build got
wrong - grep matched the literal substring "R" anywhere in a file's text
(pin names, property values, sub-unit symbol names like "R_0_1", keywords
like "res resistor"...), not specifically a real top-level part name. A
proper s-expression walk can't make that mistake: a multi-unit symbol's
sub-units (e.g. "74HC04_1_1") are nested INSIDE their parent symbol's form,
not direct children of the library form, so they're structurally excluded
without needing any special-casing.
"""
import json
import os
import sexpdata

SYMBOL_DIR = "/usr/share/kicad/symbols"
OUT_PATH = "/scratch/k2983/root-project/pcb-schematic-gen/layer1/kicad_symbol_overlap.json"

def top_level_symbol_names(sexp):
    """sexp is the parsed (kicad_symbol_lib ...) form. Return the set of
    real part names: direct children shaped like (Symbol('symbol') "NAME" ...)."""
    names = set()
    if not isinstance(sexp, list):
        return names
    for child in sexp:
        if (
            isinstance(child, list)
            and len(child) >= 2
            and isinstance(child[0], sexpdata.Symbol)
            and child[0].value() == "symbol"
            and isinstance(child[1], str)
        ):
            names.add(child[1])
    return names

overlap = {}  # part_name -> [library filenames that define it at top level]
errors = []

lib_files = sorted(f for f in os.listdir(SYMBOL_DIR) if f.endswith(".kicad_sym"))
print(f"scanning {len(lib_files)} library files")

for fname in lib_files:
    path = os.path.join(SYMBOL_DIR, fname)
    lib_name = fname[: -len(".kicad_sym")]
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        parsed = sexpdata.loads(text)
    except Exception as e:
        errors.append((fname, str(e)))
        continue
    for name in top_level_symbol_names(parsed):
        overlap.setdefault(name, []).append(lib_name)

print(f"found {len(overlap)} distinct top-level symbol names")
if errors:
    print(f"{len(errors)} files failed to parse:")
    for fname, err in errors:
        print(f"  {fname}: {err}")

with open(OUT_PATH, "w") as f:
    json.dump(overlap, f, indent=1, sort_keys=True)
print(f"wrote {OUT_PATH}")
