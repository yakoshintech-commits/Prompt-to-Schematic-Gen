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
  "nets": [{"name": "<net name>", "endpoints": [{"ref": "<matches a components[].ref>", "pin_id": "<EXACT pin id from that component's real pin list>", "pin_name": "<EXACT pin name from that component's real pin list>"}]}]
}"""


def build_system_prompt(allowed_components_json: str) -> str:
    return f"""You are designing a circuit candidate for a PCB schematic, grounded ONLY in real, verified components.

You may ONLY use the following components. This is the complete allowed vocabulary - do not invent, guess, or hallucinate any component, part_id, pin_id, or pin_name not present verbatim in this data:

{allowed_components_json}

CRITICAL RULES:
1. Every "part_id" in your output MUST be copied exactly (character for character) from an "id" field above.
2. Every "pin_id" and "pin_name" you reference MUST be copied exactly from that specific component's "pins" list above. Do not invent a pin that isn't listed, even if it seems like it should exist.
3. If the allowed vocabulary does not contain a component you'd genuinely need for a complete circuit, say so in "assumptions" rather than inventing one.

{CANDIDATE_SCHEMA_DESCRIPTION}"""


def build_user_prompt(vague_prompt: str) -> str:
    return f"Design a circuit candidate for this request: {vague_prompt}"
