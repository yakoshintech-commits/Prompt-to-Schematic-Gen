# Layer 1 Pipeline

## Purpose

Layer 1's own architecture end to end - retrieval -> generation -> hallucination filter -> verify -> score - so a future session can see how the pieces fit together without re-reading every module.

## Key facts (confirmed empirically, not assumed)

**Step 2 generation still hallucinates even with a carefully constrained prompt - this is why Step 3 exists, not a Step 2 bug to fix.** Confirmed on a real `generate_candidates()` run for "I need something to blink an LED": one candidate invented `"0402RES"` and `"0402CAP"` as part_ids - neither exists anywhere in the 241-component KG (confirmed via `kg.has_component()`). The same candidate also got `SK6812`'s real pin 2 wrong (claimed `"VSS"`, the real pin 2 is `"DIN"` - `VSS` is actually pin 1), and internally contradicted itself, using pin_id `"2"` for two different roles (`VSS` in one net, `DIN` in another) in the same candidate. The system prompt's explicit "CRITICAL RULES" reduced but did not eliminate hallucination, even for a real, correctly-retrieved component the model had full data for. Confirms the whole-pipeline design is right: generation is not the trust boundary, Step 3's deterministic check against real component data is.

**Step 1 retrieval (`layer1/retrieval.py`) - known limitations**, found by running `layer1/test_retrieval.py` against 4 varied vague prompts and inspecting real output, not assumed:

1. **Substring matching on free-text notes causes false collisions with unrelated words.** Confirmed: for "I need something to blink an LED", a plain substring-overlap version ranked unrelated ICs above the actual `LED` component - "led" as a substring matched inside "control**led**" and "coup**led**" in unrelated notes. Fixed by switching to whole-word matching for the `note` field specifically (kept substring matching for `id`/`category`/`subcategory`, since compact identifiers like `0402LED` have no word-boundary convention - "0402" and "LED" aren't separated by anything, so whole-word matching there would break the very case it's meant to catch).
2. **No stopword filtering initially let common English words ("need", "to", "an", "something") count as real keywords**, matching as substring noise across unrelated notes and outscoring the one genuinely relevant match. Fixed with a small hardcoded stopword list (see `_STOPWORDS` in `retrieval.py`) - not exhaustive, just enough to stop the worst noise for a first version.
3. **Still open, not fixed** (documented per the task spec rather than kept chasing, to avoid over-engineering a "keep it simple" first version): matching the same keyword in both the id-fields group and the note separately double-counts it, which can let a component whose *category label* happens to repeat a word also in its note (e.g. `subcategory="usb_uart_bridge"` + a note that also says "USB") edge out a more genuinely relevant component on an artificial tie. Confirmed on "something for charging a phone over USB": `CP2102N` (a USB-UART bridge, tangential) outranked `TP4056_5V_1A` (an actual USB battery charger, the literal right answer) this way.
4. **No stemming/morphology** - "charging" in a prompt won't match "charger" in a note (different word), even though they're obviously the same concept to a human. This is the class of gap the task's own TODO defers to embedding-based retrieval, not something to patch with more string rules.
5. **Genuine KG coverage gap, confirmed, not just an algorithm issue**: for "I want to connect two boards together with a cable", no generic board-to-board connector surfaced in the top-5 across any version of the scoring tried. Counted directly: the 241-set has exactly **3** `category == "connector"` components total, and all 3 are USB connectors (`USB_C_Receptacle_USB2.0`, `USB_C_Receptacle_PowerOnly_6P`, `USB_B_Micro`). There is no pin header, JST connector, or ribbon cable in this KG at all - no retrieval algorithm can surface a match that doesn't exist. This is a real limitation of the 241-component set itself, not of `retrieval.py`.

## Common mistakes to avoid

- Don't substring-match against free-text `note` fields - use whole-word matching there specifically, or short real keywords (like "led") will false-positive inside unrelated English words.
- Don't assume a retrieval gap is a bug in the matching logic before checking whether the KG actually has good coverage for that query's domain - see limitation 5 above.

## Code references

- `layer1/retrieval.py` - `retrieve_relevant_components`, `_STOPWORDS`
- `layer1/test_retrieval.py` - the 4-vague-prompt test that surfaced limitations 1-5 above
- `layer1/kg_open_schematics_store.py` - `OpenSchematicsKGStore`, the kg_store retrieval runs against

TODO.
