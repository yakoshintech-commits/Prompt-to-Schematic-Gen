# Layer 1 -> SchGen Connector

## Purpose

The missing piece between Layer 1 (vague prompt -> verified JSON candidate) and SchGen (detailed prompt -> real schematic): converting a verified candidate into the natural-language prompt SchGen expects. This is what closes the full loop - vague prompt to a real, ERC-checked KiCad schematic file - end to end.

## Key facts (confirmed empirically, not assumed)

**First genuine, fully end-to-end vague-prompt-to-schematic success, confirmed 2026-09-18.** Full chain: `"I want a small OLED display for status info"` -> Layer 1 retrieval + generation + hallucination filter + real verifier -> a `passed` candidate (`SK6812`-style grounding, this time `LCD-016N002L` + `1N4148` + `D_Small`) -> `candidate_to_detailed_prompt` -> SchGen's `verify_and_retry.py` orchestrator -> a real `.kicad_sch` file with **0 ERC errors**. Evidence: `evidence/T003-vague-to-schematic-final-e2e.log`, final schematic at `SchGen/vague_to_schematic_oled/`.

**Two clones need to agree on a shared vocabulary before this can work at all - `schgen_compatible_kg_store.py`.** Layer 1's 241-component KG and SchGen's own stock KiCad symbol library (`/usr/share/kicad/symbols/`) are two separate, only partially-overlapping worlds. Confirmed via a real grep: only 133/241 (55%) of Layer 1's parts exist as an exact-name symbol in SchGen's library. `SchGenCompatibleKGStore` wraps a base kg_store and restricts `component_map`/`kg_component_map` to that 133-part intersection, computed once and saved to `kicad_symbol_overlap.json`, so anything Layer 1 verifies is guaranteed placeable - fixing this at the generation source, not patching around it downstream.

**A "passed" Layer 1 candidate is electrically grounded, not necessarily a sensible circuit - and that's a real, already-known limitation, not a new bug.** The OLED candidate above assigned `1N4148` (a diode) to ref `R1` and wired it as if it were a pull-up resistor; three of the LCD's control pins (`RS`/`E`/`RW`) all got tied to the same diode's cathode. Layer 1's verifier only checks "does this part/pin exist" and "is this pin connected to a net" - not circuit-level semantic correctness. This is fine for testing the connector mechanism itself (which only needs grounded, real data to convert faithfully), but worth remembering before treating a `passed` candidate as a good design.

**Prompt phrasing matters for SchGen's own generation stability, but isn't the primary hallucination defense - `candidate_to_detailed_prompt`'s grouping.** Groups refs sharing a part_id into one clause (`"D1, and C1 as 2 separate instances of a D_Small"`) instead of repeating an identical phrase per-ref. Originally built to test a (later-disproven, see `skills/schgen-integration/SKILL.md`) repetition-priming hypothesis for a different bug, but kept anyway since collapsed phrasing is objectively cleaner input regardless.

**Real, genuine KG-vs-reality mismatches still surface even inside the 133-part "compatible" overlap - and SchGen's own retry loop is what catches and fixes them, not Layer 1.** The `1N4148` KG entry (PCBSchemaGen_v2's data) records pin names `A`/`K` (real datasheet anode/cathode convention). The *actual* stock KiCad symbol for `1N4148` uses anonymous numbered pins (`~`, no text name) - `SchGenCompatibleKGStore` only checked that the part_id exists as a symbol, not that its pin *names* match. Attempt 1 of the real end-to-end run failed on exactly this (`ValueError: Pin A not found in symbol R1`, SchGen's own fuzzy-match fallback scored the correction at 0.0 and correctly refused to guess); the real error was fed back through `verify_and_retry.py`'s retry loop, and attempt 2 passed cleanly. This is the system working as designed, not a gap - it's a good demonstration of why the retry loop exists at the SchGen layer even when Layer 1's own checks pass.

## Common mistakes to avoid

- Don't feed a Layer 1 candidate's part_ids straight to SchGen without checking they exist in SchGen's own symbol library first - a `passed` Layer 1 candidate can still reference a part with zero real KiCad symbol, forcing SchGen to guess.
- Don't assume "part_id exists as a symbol" also means "pin names match between the two data sources" - confirmed above that they can genuinely diverge even for parts that pass the existence check. This is exactly why SchGen's own build-time verification and retry loop still matter, even downstream of Layer 1's grounding.
- Don't treat a `passed` Layer 1 candidate as proof of good circuit design - it only proves the stated facts are real and connected, not that the circuit makes sense.

## Code references

- `layer1/schgen_compatible_kg_store.py` - `SchGenCompatibleKGStore`, the vocabulary-intersection wrapper
- `layer1/schgen_bridge.py` - `candidate_to_detailed_prompt`, the JSON-candidate-to-prose converter
- `layer1/kicad_symbol_overlap.json` - the real part_id -> stock KiCad library mapping
- `SchGen/schematic_generation/verify_and_retry.py` - the orchestrator that actually catches and retries on mismatches like the `1N4148` one above
- `evidence/T003-vague-to-schematic-final-e2e.log` - the real end-to-end run, both the attempt-1 failure and attempt-2 success
