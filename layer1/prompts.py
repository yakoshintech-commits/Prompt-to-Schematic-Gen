"""
Prompt text for Layer 1's constrained candidate generator, kept separate
from generate_candidates.py's logic per T001 Step 2.
"""

CANDIDATE_SCHEMA_DESCRIPTION = """\
Output STRICT JSON only, no markdown code fences, no commentary before or after. Schema:
{
  "id": "<short slug>",
  "name": "<short human-readable name>",
  "summary": "<1-2 sentence description of the design>",
  "tradeoffs": "<1-2 sentences on what this design trades off>",
  "assumptions": "<1-2 sentences on assumptions made>",
  "components": [{"ref": "<reference designator, e.g. R1>", "part_id": "<EXACT part_id from the allowed vocabulary below>"}],
  "nets": [{"name": "<net name>", "endpoints": [{"ref": "<matches a components[].ref>", "pin_choice": "<EXACT one of the allowed '<part_id>::<pin_id>::<pin_name>' choices for the component that ref actually uses>"}]}]
}
Note: when a candidate schema is enforced (format-constrained generation), "pin_choice" is a closed enum of every real (part_id, pin_id, pin_name) triple in the allowed vocabulary above - you cannot type a value outside this list. Pick the ref's OWN component's pin, not a different component's."""


def build_system_prompt(allowed_components_json: str) -> str:
    return f"""You are designing a circuit candidate for a PCB schematic, grounded ONLY in real, verified components.

You may ONLY use the following components. This is the complete allowed vocabulary - do not invent, guess, or hallucinate any component, part_id, pin_id, or pin_name not present verbatim in this data:

{allowed_components_json}

CRITICAL RULES:
1. Every "part_id" in your output MUST be copied exactly (character for character) from an "id" field above.
2. Every "pin_id" and "pin_name" you reference MUST be copied exactly from that specific component's "pins" list above. Do not invent a pin that isn't listed, even if it seems like it should exist.
3. If the allowed vocabulary does not contain a component you'd genuinely need for a complete circuit, say so in "assumptions" rather than inventing one.
4. Use the SMALLEST number of components that forms a genuinely complete, correctly-wired circuit. Do not add a second instance of the same (or a similar, unrelated) component just because it appears in the allowed vocabulary - only repeat a component if the design genuinely needs more than one (e.g. two crystal load capacitors). Every component you DO include must have every one of its required pins connected in "nets" before you finish. A smaller design where every pin is wired is correct; a larger design with unconnected pins is not - components and nets are both capped at 8 entries, so budget them for the parts that actually need to be there.
5. Give each ref a designator prefix matching its real component type (a resistor is "R", a capacitor "C", an IC/module is "U", a diode/MOSFET/transistor is "D"/"Q") - never reuse "R"/"C"/"D" for an unrelated IC or module.

{CANDIDATE_SCHEMA_DESCRIPTION}"""


def build_user_prompt(vague_prompt: str) -> str:
    return f"Design a circuit candidate for this request: {vague_prompt}"


def build_feedback_prompt(error_text: str) -> str:
    """
    Fed as a genuine user turn AFTER the previous attempt is replayed as an
    assistant turn (see generate_candidates.py's retry loop) - not appended
    as a second user message. Confirmed elsewhere this session (SchGen's own
    retry loop) that a bare user->user pair is not reliably followed even
    when it contains the exact correct answer; a real multi-turn correction
    (assistant's prior attempt, then a user reply pointing at the specific
    real error) is the structure these models actually respond to.
    """
    return f"""That candidate failed verification. Here is the real error, verbatim:
###
{error_text}
###
Fix the specific issue above. Every part_id and pin must still come EXACTLY from the allowed vocabulary in the system prompt - do not invent a replacement that isn't in it. If the fix requires connecting a pin to another component (e.g. a suggestion to add a driver or pull resistor), that component's ref MUST also appear in "components" with its own part_id - do not reference a ref in "nets" that isn't listed in "components". Output a corrected candidate as a single JSON object (not an array)."""
