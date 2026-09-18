"""
Component retrieval: cheap keyword-overlap ranking over a kg_store's
components. Keep this simple for a first version - see the TODO below.
"""

import re

# Common English words that would otherwise count as "keywords" and match as
# substrings inside unrelated component notes (e.g. "an" inside "channel"),
# drowning out real single-keyword matches. Confirmed empirically: without
# this, "I need something to blink an LED" ranked an unrelated USB connector
# (score 3, matching "need"/"to"/"an" as substring fragments) above the
# actual 0402LED component (score 1, matching only "led"). Not exhaustive -
# just enough to stop the worst false-positive noise for a first version.
_STOPWORDS = {
    "i", "a", "an", "the", "to", "of", "for", "with", "and", "or", "is",
    "it", "on", "in", "at", "as", "be", "by", "do", "if", "so", "up",
    "add", "need", "want", "make", "use", "some", "something", "way",
    "my", "me", "we", "you", "that", "this", "these", "those",
}


def retrieve_relevant_components(vague_prompt: str, kg_store, top_k: int = 15) -> list[dict]:
    """
    Rank kg_store's components by keyword overlap against the vague prompt,
    matching against each component's id, category, subcategory, and note
    fields. Returns the top_k most relevant real components with their full
    pin list and constraints intact (the raw component dicts, unmodified).

    # TODO: replace with embedding-based retrieval if keyword matching proves
    # too shallow for genuinely vague prompts - not building that now.
    """
    keywords = {
        kw for kw in re.findall(r"[a-z0-9]+", vague_prompt.lower())
        if len(kw) > 1 and kw not in _STOPWORDS
    }

    scored = []
    for comp in kg_store.kg_component_map.values():
        # id/category/subcategory are compact identifiers with no word-boundary
        # convention (e.g. "0402LED" has no separator between "0402" and "LED"),
        # so substring matching is correct there. note is free-text English
        # prose, where substring matching is wrong: confirmed empirically that
        # "led" as a substring matched inside "controlled" and "coupled" in
        # unrelated notes, tying (and beating, via arbitrary dict order) the
        # actual 0402LED component. Use whole-word matching for note only.
        id_fields_text = " ".join(
            str(comp.get(field, "")) for field in ("id", "category", "subcategory")
        ).lower()
        note_words = set(re.findall(r"[a-z0-9]+", str(comp.get("note", "")).lower()))
        score = sum(1 for kw in keywords if kw in id_fields_text)
        score += sum(1 for kw in keywords if kw in note_words)
        if score > 0:
            scored.append((score, comp))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [comp for _, comp in scored[:top_k]]
