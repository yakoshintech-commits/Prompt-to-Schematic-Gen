# Full-Stack Integration: Layer 1 -> Ollama-Served SchGen

## Purpose

T002 (SchGen -> Ollama) and T003 (Layer 1 -> SchGen connector) were each built and tested separately - T003's end-to-end test used the *original PyTorch* SchGen pipeline, and T002's tests fed hand-written prompts straight to the Ollama-served merged model, never through Layer 1. The two halves had never been run together as one continuous flow. This is that test.

## Key facts (confirmed empirically, not assumed)

**The first combined run failed - for two real, fixable reasons, neither of which showed up when T002 and T003 were tested separately.** Full chain: `"I want a small OLED display for status info"` -> Layer 1 (retrieval + generation + hallucination filter + real verifier, reused the already-verified `oled_status` candidate) -> `candidate_to_detailed_prompt` -> `verify_and_retry_ollama.py` (T002's retry loop) -> build + ERC. Result on the first attempt: exhausted all 3 retries, never reached a clean build. Evidence: `evidence/T004-full-integration-schgen-stage.log`.

1. **`verify_and_retry_ollama.py` didn't strip markdown code fences.** T002's earlier spot-check prompts (hand-written, simpler, more conversational) happened to get fence-free responses back from Ollama. `candidate_to_detailed_prompt`'s denser, more fact-listing prompt style triggered the model to wrap its answer in a ```` ```python ... ``` ```` fence, and the retry script executed that literally - `SyntaxError: invalid syntax` on the fence line itself, identically on attempts 1 and 2 (the retry loop kept feeding back a build error the model couldn't act on, since the actual cause wasn't in the code logic).
2. **`candidate_to_detailed_prompt` never told SchGen which real KiCad library each part lives in.** It names the part (e.g. `LCD-016N002L`) but not its library, forcing SchGen to guess `symbol_lib` on its own. It guessed `"LCD"` - a real-sounding but nonexistent library (`FileNotFoundError: .../LCD.kicad_sym`). The real library, per `kicad_symbol_overlap.json` (already computed by `SchGenCompatibleKGStore` for exactly this purpose, just not being used by the prompt-building code) is `Display_Character`. This is a case where a 100%-correct Layer 1 candidate still produced a build failure downstream, because the bridge between them dropped information Layer 1 already had.

**Both are now fixed, and the same prompt passes cleanly on the first attempt.** `_strip_code_fence` added to `verify_and_retry_ollama.py` (defensive parsing, same category of fix as `layer1/generate_candidates.py`'s `_parse_candidate_json`). `candidate_to_detailed_prompt` now includes the real library name inline (`"...a LCD-016N002L, in the KiCad library \"Display_Character\"..."`) via the `symbol_lib_for()` lookup that already existed but wasn't being called. Re-ran the identical candidate end to end: **0 ERC errors, first attempt, no retry needed.** Evidence: `evidence/T004-full-integration-schgen-stage-v2.log`.

## T005: comprehensive test across 6 more domains (2026-09-18)

Sponsor decision: run this broad test *before* fixing T006/T007/T008 (findings from earlier single runs), on the reasoning that fixing hypothetical problems before seeing real failure rates risks wasted effort. Picked 6 domains not yet tested through the full combined chain, chosen from a real scan of the SchGen-compatible KG's actual category breakdown (not guessed): temperature sensing (`DS18B20`), motor driving (`TB6612FNG`), a real-time clock (`DS3232M`), an op-amp (`LM358`), a classic 555 timer (`NE555D`), and a push button.

**Layer 1 stage: 3/6 reached a `passed` candidate** (op-amp, 555 timer, push button). The other 3 (temp sensor, motor driver, RTC) hit `failed_checks` - the real deterministic verifier correctly catching genuinely incomplete wiring after exhausting the retry budget, not a bug in the check itself. Evidence: `evidence/T005-layer1-batch.log`.

**SchGen stage: 3/3 of the reachable candidates eventually got 0 ERC errors** (op-amp and 555 timer on the first attempt, push button via one retry). Evidence: `evidence/T005-schgen-batch.log`.

**Confirmed T006 and T007 are real, recurring issues, not one-offs:**
- T006's symbol-selection JSON key mismatch (`libName` vs `lib_name`) recurred in 2 of the 3 SchGen runs (op-amp, 555 timer) - always degrading gracefully, never hard-failing, but frequent.
- T007's ref-designator/category mismatch recurred again: the op-amp candidate assigned `1N4148` (a diode) to ref `R1`, the same pattern as the earlier OLED case - a second independent real instance, not a fluke.

**Found a genuinely new bug (T009), not previously identified, specifically because this test finally exercised generic passive components:** the push-button candidate's plain resistor (`part_id="R"`) resolved via `symbol_lib_for()` to library `"74xx_IEEE"` - wrong, causing a real build failure on attempt 1 (`ValueError: Symbol 'R' not found in library`). It recovered on attempt 2 via retry, but that's luck, not a fix. Root cause: `kicad_symbol_overlap.json`'s original grep-based construction (from T003) matches the literal substring `"R"` anywhere in a `.kicad_sym` file - including inside unrelated pin names/properties - not specifically as a top-level symbol name. For a generic ID this short, that produces a long, mostly-wrong candidate list (17 libraries for `"R"` alone, correct answer `"Device"` buried in the middle), and `symbol_lib_for()` just takes the first one arbitrarily. Likely affects `C`, `L`, `D`, and other short generic IDs too - not yet checked.

## Common mistakes to avoid

- Don't assume a component tested in isolation stays correct once connected to a different upstream/downstream piece - both failures here were real integration-boundary bugs, invisible to either T002's or T003's own separate tests.
- Don't assume a model's response format (fenced vs. not) is stable across prompt styles - defensively strip formatting rather than assuming based on what earlier, differently-shaped prompts happened to return.
- When a bridge/converter function has access to grounding data (like a real library name), use it - leaving it out just moves the guessing (and the hallucination risk) one step downstream instead of removing it.

## Code references

- `SchGen/schematic_generation/verify_and_retry_ollama.py` - `_strip_code_fence`
- `layer1/schgen_bridge.py` - `candidate_to_detailed_prompt`'s `symbol_lib_for()` lookup
- `evidence/T004-full-integration-schgen-stage.log` - the first, failing run
- `evidence/T004-full-integration-schgen-stage-v2.log` - the fixed, passing run
