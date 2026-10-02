"""
Stage candidate KG entries for every real KiCad symbol NOT already curated
into kg_open_schematics.json - the "20,618 real symbols, only 243 curated"
gap identified 2026-10-02. Deliberately writes to a SEPARATE staging file,
never touches the live KG (which the current full-pipeline validation run
is actively reading) - this is draft data for later human/LLM review, not
an auto-merge.

Confidence discipline, matching this project's established "don't guess,
don't invent a role that could be wrong" rule (see phase2_checks.py's
_GENERIC_ROLE_FAMILIES, and the Antenna/Stepper_Motor_bipolar curation
precedent): only label a pin_role when the real pin NAME is an exact,
unambiguous match (GND/VSS -> supply_gnd, VCC/VDD -> supply_vdd). Every
other pin is left role-less rather than guessed. Every entry is tagged
needs_review=True - this is a draft pool to curate from, not a shipped
addition.
"""
import json
import os
import sexpdata

SYMBOL_DIR = "/usr/share/kicad/symbols"
KG_PATH = "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2/kg/kg_open_schematics.json"
OUT_PATH = "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2/kg/kg_candidate_pool.json"

_GND_NAMES = {"GND", "VSS", "AGND", "DGND", "PGND"}
_VDD_NAMES = {"VCC", "VDD", "VBAT", "AVDD", "DVDD", "V+", "VIN", "VBUS"}

# Libraries that hold schematic CONVENTION symbols, not real purchasable
# components (power-flag symbols, title-block graphics, SPICE-only
# simulation models) - excluded from the candidate pool entirely rather
# than mislabeled as "unknown" real parts.
_EXCLUDED_LIBS = {"power", "graphic", "simulation_spice"}

# Comprehensive library-name -> category mapping, built directly from the
# real 221-library listing (2026-10-02) rather than a 25-library sample -
# KiCad's own library naming convention is clean enough that this covers
# effectively all of them. Still a HINT, not authoritative (every entry
# keeps needs_review=True) - a few families are deliberately coarse
# (e.g. all MCU_* -> ic/mcu) since finer distinction needs per-symbol
# content, not just the library name.
_LIB_CATEGORY_HINTS = {
    "4xxx": "ic", "4xxx_ieee": "ic", "74xgxx": "ic", "74xx": "ic", "74xx_ieee": "ic",
    "amplifier_audio": "ic", "amplifier_buffer": "ic", "amplifier_current": "ic",
    "amplifier_difference": "ic", "amplifier_instrumentation": "ic", "amplifier_operational": "ic",
    "amplifier_video": "ic", "analog": "ic", "analog_adc": "ic", "analog_dac": "ic",
    "analog_switch": "ic", "audio": "ic", "battery_management": "ic", "buffer": "ic",
    "cpld_altera": "ic", "cpld_microchip": "ic", "cpld_renesas": "ic", "cpld_xilinx": "ic",
    "cpu": "ic", "cpu_nxp_6800": "ic", "cpu_nxp_68000": "ic", "cpu_nxp_imx": "ic",
    "cpu_powerpc": "ic", "comparator": "ic", "connector": "connector",
    "connector_audio": "connector", "connector_generic": "connector",
    "connector_generic_mountingpin": "connector", "connector_generic_shielded": "connector",
    "converter_acdc": "ic", "converter_dcdc": "ic", "device": "passive",
    "dsp_analogdevices": "ic", "dsp_freescale": "ic", "dsp_microchip_dspic33": "ic",
    "dsp_motorola": "ic", "dsp_texas": "ic",
    "diode": "diode", "diode_bridge": "diode", "diode_laser": "diode",
    "display_character": "ic", "display_graphic": "ic", "driver_display": "ic",
    "driver_fet": "ic", "driver_haptic": "ic", "driver_led": "ic", "driver_motor": "ic",
    "driver_relay": "ic", "driver_tec": "ic", "fpga_colognechip_gatemate": "ic",
    "fpga_efinix_trion": "ic", "fpga_lattice": "ic", "fpga_microsemi": "ic",
    "fpga_xilinx": "ic", "fpga_xilinx_artix7": "ic", "fpga_xilinx_kintex7": "ic",
    "fpga_xilinx_spartan6": "ic", "fpga_xilinx_virtex5": "ic", "fpga_xilinx_virtex6": "ic",
    "fpga_xilinx_virtex7": "ic", "fiber_optic": "ic", "filter": "ic", "gpu": "ic",
    "interface": "ic", "interface_can_lin": "ic", "interface_currentloop": "ic",
    "interface_ethernet": "ic", "interface_expansion": "ic", "interface_hdmi": "ic",
    "interface_hid": "ic", "interface_linedriver": "ic", "interface_optical": "ic",
    "interface_telecom": "ic", "interface_uart": "ic", "interface_usb": "ic",
    "isolator": "ic", "isolator_analog": "ic", "jumper": "passive", "led": "passive",
    "logic_leveltranslator": "ic", "logic_programmable": "ic",
    "mcu_analogdevices": "ic", "mcu_cypress": "ic", "mcu_dialog": "ic",
    "mcu_espressif": "ic", "mcu_intel": "ic", "mcu_microchip_8051": "ic",
    "mcu_microchip_atmega": "ic", "mcu_microchip_attiny": "ic", "mcu_microchip_avr": "ic",
    "mcu_microchip_avr_dx": "ic", "mcu_microchip_pic10": "ic", "mcu_microchip_pic12": "ic",
    "mcu_microchip_pic16": "ic", "mcu_microchip_pic18": "ic", "mcu_microchip_pic24": "ic",
    "mcu_microchip_pic32": "ic", "mcu_microchip_sama": "ic", "mcu_microchip_samd": "ic",
    "mcu_microchip_same": "ic", "mcu_microchip_saml": "ic", "mcu_microchip_samv": "ic",
    "mcu_module": "devboard", "mcu_nxp_coldfire": "ic", "mcu_nxp_hc11": "ic",
    "mcu_nxp_hc12": "ic", "mcu_nxp_hcs12": "ic", "mcu_nxp_kinetis": "ic",
    "mcu_nxp_lpc": "ic", "mcu_nxp_mac7100": "ic", "mcu_nxp_mcore": "ic",
    "mcu_nxp_ntag": "ic", "mcu_nxp_s08": "ic", "mcu_nordic": "ic", "mcu_parallax": "ic",
    "mcu_raspberrypi": "ic", "mcu_renesas_synergy_s1": "ic", "mcu_stc": "ic",
    "mcu_st_stm32c0": "ic", "mcu_st_stm32f0": "ic", "mcu_st_stm32f1": "ic",
    "mcu_st_stm32f2": "ic", "mcu_st_stm32f3": "ic", "mcu_st_stm32f4": "ic",
    "mcu_st_stm32f7": "ic", "mcu_st_stm32g0": "ic", "mcu_st_stm32g4": "ic",
    "mcu_st_stm32h5": "ic", "mcu_st_stm32h7": "ic", "mcu_st_stm32l0": "ic",
    "mcu_st_stm32l1": "ic", "mcu_st_stm32l4": "ic", "mcu_st_stm32l5": "ic",
    "mcu_st_stm32mp1": "ic", "mcu_st_stm32u5": "ic", "mcu_st_stm32wb": "ic",
    "mcu_st_stm32wba": "ic", "mcu_st_stm32wl": "ic", "mcu_st_stm8": "ic",
    "mcu_sifive": "ic", "mcu_siliconlabs": "ic", "mcu_texas": "ic",
    "mcu_texas_msp430": "ic", "mcu_texas_simplelink": "ic", "mcu_wch_ch32v0": "ic",
    "mcu_wch_ch32v3": "ic", "mechanical": "mechanical", "memory_eeprom": "ic",
    "memory_eprom": "ic", "memory_flash": "ic", "memory_nvram": "ic", "memory_ram": "ic",
    "memory_rom": "ic", "memory_uniqueid": "ic", "motor": "motor", "oscillator": "ic",
    "potentiometer_digital": "ic", "power_management": "ic", "power_protection": "ic",
    "power_supervisor": "ic", "rf": "ic", "rf_am_fm": "ic", "rf_amplifier": "ic",
    "rf_bluetooth": "ic", "rf_filter": "ic", "rf_gps": "ic", "rf_gsm": "ic",
    "rf_mixer": "ic", "rf_module": "ic", "rf_nfc": "ic", "rf_rfid": "ic",
    "rf_switch": "ic", "rf_wifi": "ic", "rf_zigbee": "ic", "reference_current": "ic",
    "reference_voltage": "ic", "regulator_controller": "ic", "regulator_current": "ic",
    "regulator_linear": "ic", "regulator_switchedcapacitor": "ic",
    "regulator_switching": "ic", "relay": "relay", "relay_solidstate": "relay",
    "security": "ic", "sensor": "ic", "sensor_audio": "ic", "sensor_current": "ic",
    "sensor_distance": "ic", "sensor_energy": "ic", "sensor_gas": "ic",
    "sensor_humidity": "ic", "sensor_magnetic": "ic", "sensor_motion": "ic",
    "sensor_optical": "ic", "sensor_pressure": "ic", "sensor_proximity": "ic",
    "sensor_temperature": "ic", "sensor_touch": "ic", "sensor_voltage": "ic",
    "switch": "switch", "timer": "ic", "timer_pll": "ic", "timer_rtc": "ic",
    "transformer": "transformer", "transistor_array": "transistor",
    "transistor_bjt": "transistor", "transistor_fet": "MOSFET",
    "transistor_fet_other": "MOSFET", "transistor_igbt": "MOSFET",
    "transistor_power_module": "MOSFET", "triac_thyristor": "thyristor",
    "valve": "tube", "video": "ic",
}


def unq(s):
    if isinstance(s, str) and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def find_prop(sym_form, prop_name):
    for child in sym_form:
        if (isinstance(child, list) and len(child) >= 3
                and isinstance(child[0], sexpdata.Symbol) and child[0].value() == "property"
                and unq(child[1]) == prop_name):
            return unq(child[2])
    return None


def extract_pins(sym_form):
    pins = []

    def walk(node):
        if not isinstance(node, list):
            return
        if node and isinstance(node[0], sexpdata.Symbol) and node[0].value() == "pin":
            pin_name = pin_number = None
            for child in node[1:]:
                if isinstance(child, list) and child and isinstance(child[0], sexpdata.Symbol):
                    tag = child[0].value()
                    if tag == "name" and len(child) >= 2:
                        pin_name = unq(child[1])
                    elif tag == "number" and len(child) >= 2:
                        pin_number = unq(child[1])
            if pin_number is not None:
                pins.append({"num": pin_number, "name": pin_name if pin_name else "~"})
        for child in node:
            walk(child)

    walk(sym_form)
    # de-dup (multi-unit symbols repeat shared power-unit pins per sub-unit)
    seen = set()
    out = []
    for p in pins:
        key = (p["num"], p["name"])
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def infer_pin_roles(pins):
    roles = {}
    for p in pins:
        name = p["name"].upper()
        if name in _GND_NAMES:
            roles[p["name"]] = "supply_gnd"
        elif name in _VDD_NAMES:
            roles[p["name"]] = "supply_vdd"
    return roles


def infer_generic_constraints(pins, roles):
    gnd_pins = [p["name"] for p in pins if roles.get(p["name"]) == "supply_gnd"]
    vdd_pins = [p["name"] for p in pins if roles.get(p["name"]) == "supply_vdd"]
    if len(set(gnd_pins)) == 1 and len(set(vdd_pins)) == 1:
        return [{"type": "supply_pair", "vdd_pin": vdd_pins[0], "gnd_pin": gnd_pins[0]}]
    return []


existing_kg = json.load(open(KG_PATH))
existing_comps = existing_kg["components"] if isinstance(existing_kg, dict) else existing_kg
already_curated = {c["id"] for c in existing_comps}
print(f"already curated: {len(already_curated)}", flush=True)

lib_files = sorted(f for f in os.listdir(SYMBOL_DIR) if f.endswith(".kicad_sym"))
print(f"scanning {len(lib_files)} library files", flush=True)

candidates = {}
parse_errors = []

for fi, fname in enumerate(lib_files, 1):
    lib_name = fname[: -len(".kicad_sym")]
    if lib_name.lower() in _EXCLUDED_LIBS:
        continue
    path = os.path.join(SYMBOL_DIR, fname)
    try:
        parsed = sexpdata.loads(open(path, "r", encoding="utf-8").read())
    except Exception as e:
        parse_errors.append((fname, str(e)))
        continue

    top_level = [
        child for child in parsed
        if isinstance(child, list) and len(child) >= 2
        and isinstance(child[0], sexpdata.Symbol) and child[0].value() == "symbol"
        and isinstance(child[1], str)
    ]
    by_name = {unq(c[1]): c for c in top_level}

    for name, sym_form in by_name.items():
        if name in already_curated or name in candidates:
            continue

        extends_name = None
        for child in sym_form[2:]:
            if (isinstance(child, list) and len(child) >= 2
                    and isinstance(child[0], sexpdata.Symbol) and child[0].value() == "extends"):
                extends_name = unq(child[1])

        resolved_form = sym_form
        if extends_name and extends_name in by_name:
            resolved_form = by_name[extends_name]

        pins = extract_pins(resolved_form)
        if not pins:
            continue  # power-symbol-only or graphics-only entries, nothing to curate

        description = find_prop(sym_form, "ki_description") or find_prop(sym_form, "Description") or ""
        category_hint = _LIB_CATEGORY_HINTS.get(lib_name.lower(), "unknown")
        roles = infer_pin_roles(pins)
        constraints = infer_generic_constraints(pins, roles)

        candidates[name] = {
            "id": name,
            "source_library": lib_name,
            "category_hint": category_hint,
            "note": description,
            "pins": [{"num": p["num"], "name": p["name"]} for p in pins],
            "pin_roles": roles,
            "generic_constraints": constraints,
            "needs_review": True,
        }

    if fi % 50 == 0:
        print(f"  [{fi}/{len(lib_files)}] libraries scanned, {len(candidates)} candidates so far", flush=True)

print(f"\ntotal new candidate symbols staged: {len(candidates)}", flush=True)
if parse_errors:
    print(f"{len(parse_errors)} libraries failed to parse: {[f for f,_ in parse_errors]}", flush=True)

with open(OUT_PATH, "w") as f:
    json.dump(list(candidates.values()), f, indent=2)
print(f"wrote {OUT_PATH}", flush=True)

# Quick summary for review, not a commitment to use any of it as-is.
by_cat = {}
with_roles = 0
for c in candidates.values():
    by_cat[c["category_hint"]] = by_cat.get(c["category_hint"], 0) + 1
    if c["pin_roles"]:
        with_roles += 1
print("\nby category_hint:", json.dumps(by_cat, indent=2), flush=True)
print(f"candidates with at least one confidently-inferred pin role: {with_roles}/{len(candidates)}", flush=True)
