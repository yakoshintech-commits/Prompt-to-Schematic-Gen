# Layer 1 Pipeline

## Purpose

Layer 1's own architecture end to end - retrieval -> generation -> hallucination filter -> verify -> score - so a future session can see how the pieces fit together without re-reading every module.

## Key facts (confirmed empirically, not assumed)

**Pipeline shape** (`layer1/pipeline.py`'s `run_layer1`, built Step 5):
```
vague_prompt
  -> retrieve_relevant_components (Step 1: keyword-overlap over kg_store)
  -> generate_candidates (Step 2: local LLM, constrained to that vocabulary, n candidates)
  -> for each candidate: verify_candidate (Step 3 validate_parts_exist first,
     early-exit to "rejected" on failure; Step 4 real PCBSchemaGen_v2 verifier
     otherwise -> "passed" or "failed_checks")
  -> for each candidate: weighted score (cost placeholder + simplicity +
     part_availability, see _score_candidate)
  -> ranked = sorted by (verification_status passed-first, then -score)
  -> {"candidates": [...all, unranked order...], "ranked": [...]}
```
Does not auto-pick a winner - returns the full ranked list for a human (or a future UI) to choose from.

**The explicit status-priority ranking rule does real, non-redundant work** - confirmed by deliberately choosing weights (`simplicity=0.8`, others low) where a simple `failed_checks` candidate's raw weighted score (0.45) exceeds a complex `passed` candidate's (0.19). Sorting by raw score alone would have ranked the failed one first; the actual `rank_key`'s `(status_priority, -score)` tuple correctly puts the passed candidate first regardless. With the *default* weights specifically, `part_availability`'s 0.3 weight alone is large enough that a passed candidate always outscores a failed one on raw score too (0.3 exceeds simplicity's entire possible range under those weights) - so this override only becomes essential once weights are tuned away from the defaults, which is exactly why it exists as an explicit rule rather than relying on score alone.

**A real end-to-end `run_layer1` run on "I need something to blink an LED" (n=3) rejected all 3 candidates** - each invented a part_id that sounds like a real, common component (`NE555`, a genuinely real 555 timer IC; `74HC74`, a genuinely real flip-flop; `R_1k`, a plausible-looking resistor-with-value naming convention) but none exist in this specific 241-component KG. This is a different hallucination pattern than Step 2's earlier finding (fabricated-looking IDs like `0402RES`) - here the model reached for real-world component knowledge from its training data instead of the provided vocabulary, which is arguably a harder case to prompt away entirely. The pipeline's mechanics (scoring, ranking, rejection) all worked correctly regardless - this is a generation-quality observation, not a Step 5 bug. Worth revisiting if this pattern turns out to be common once Step 6's varied-prompt testing runs.

**Step 2 generation still hallucinates even with a carefully constrained prompt - this is why Step 3 exists, not a Step 2 bug to fix.** Confirmed on a real `generate_candidates()` run for "I need something to blink an LED": one candidate invented `"0402RES"` and `"0402CAP"` as part_ids - neither exists anywhere in the 241-component KG (confirmed via `kg.has_component()`). The same candidate also got `SK6812`'s real pin 2 wrong (claimed `"VSS"`, the real pin 2 is `"DIN"` - `VSS` is actually pin 1), and internally contradicted itself, using pin_id `"2"` for two different roles (`VSS` in one net, `DIN` in another) in the same candidate. The system prompt's explicit "CRITICAL RULES" reduced but did not eliminate hallucination, even for a real, correctly-retrieved component the model had full data for. Confirms the whole-pipeline design is right: generation is not the trust boundary, Step 3's deterministic check against real component data is.

**Step 3 hallucination filter (`layer1/validate_facts.py`) catches exactly the failure modes Step 2 actually produces**, confirmed with 3 hand-built synthetic candidates (grounded / hallucinated part_id / hallucinated pin) - see `layer1/test_validate_facts.py` for real output. Deliberately checks the exact `(pin_id, pin_name)` *pair* against each real pin, not either field alone - a candidate can get `pin_id` right and `pin_name` wrong (or vice versa) and still be wrong, which is precisely what happened in the real Step 2 hallucination above (`SK6812` pin 2's real name is `"DIN"`, not the claimed `"VSS"` - checking `pin_id` alone would have missed this). Fails fast on the first mismatch found (not a full report) - full multi-error reporting is the real verifier's (Step 4) job, not this filter's.

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
