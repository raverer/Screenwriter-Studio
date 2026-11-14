"""Structured extraction of Story Bible candidates from screenplay text."""
import json

FIELD_SCHEMAS = {
    "character": {
        "age", "occupation_or_role", "personality", "goal_motivation",
        "relationships", "continuity_notes",
    },
    "location": {
        "place_type", "description", "atmosphere_time", "key_details",
    },
    "prop": {
        "description", "owner_custodian", "story_significance", "continuity_notes",
    },
    "timeline": {
        "when", "event", "characters_involved", "consequences",
    },
}


def build_extraction_prompt(screenplay):
    """Build a conservative prompt that extracts only screenplay-supported facts."""
    if not isinstance(screenplay, str) or not screenplay.strip():
        raise ValueError("A non-empty screenplay is required for extraction.")

    return f"""Extract a draft Story Bible from the screenplay below.
Only include details directly supported by the screenplay. Do not invent ages,
occupations, relationships, locations, props, chronology or motivations.
When a fact is unknown or ambiguous, omit that field. Use concise plain-text
strings for all data values. Keep exact character and location names consistent.
Do not include dialogue as a character fact unless it establishes a durable fact.
Do not create an entry for incidental objects unless they matter to the story.

Return ONLY valid JSON with this structure:
{{
  "entries": [
    {{
      "category": "character",
      "name": "Exact character name",
      "data": {{
        "age": "30",
        "occupation_or_role": "Software engineer",
        "personality": "Reserved and shy",
        "goal_motivation": "Wants to build a meaningful relationship",
        "relationships": "On a date with Mira",
        "continuity_notes": "Wears a silver wristwatch"
      }}
    }},
    {{
      "category": "location",
      "name": "Exact location name",
      "data": {{
        "place_type": "Exterior",
        "description": "A rocky shoreline",
        "atmosphere_time": "Night",
        "key_details": "Waves and a rocky shoreline"
      }}
    }},
    {{
      "category": "prop",
      "name": "Silver wristwatch",
      "data": {{
        "description": "A silver wristwatch",
        "owner_custodian": "Aarav",
        "story_significance": "A recurring visual detail",
        "continuity_notes": "Keep with Aarav"
      }}
    }},
    {{
      "category": "timeline",
      "name": "First date",
      "data": {{
        "when": "Night",
        "event": "Aarav and Mira meet for a date",
        "characters_involved": "Aarav, Mira",
        "consequences": "They walk together along the beach"
      }}
    }}
  ]
}}

Use only the category-specific field names shown above. The examples illustrate
the structure only; do not copy facts that are absent from the screenplay.
If no reliable facts can be extracted, return {{"entries": []}}.

SCREENPLAY:
{screenplay[:18000]}"""


def _extract_json_object(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("The model returned an empty extraction response.")
    text = raw.strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("The model did not return a JSON object.")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid extraction JSON: {exc.msg}. Try extracting again.") from exc


def parse_extraction_response(raw):
    """Validate extraction JSON and return candidate records without saving them."""
    payload = _extract_json_object(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError("Extraction must contain an 'entries' list.")

    records = []
    seen = set()
    for index, entry in enumerate(payload["entries"], start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {index} must be an object.")
        category = entry.get("category")
        name = entry.get("name")
        data = entry.get("data")
        if category not in FIELD_SCHEMAS:
            raise ValueError(f"Entry {index} has an unsupported category: {category!r}.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Entry {index} must have a non-empty name.")
        if not isinstance(data, dict):
            raise ValueError(f"Entry {index} must have a data object.")

        unknown_fields = set(data) - FIELD_SCHEMAS[category]
        if unknown_fields:
            fields = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Entry {index} has unsupported {category} field(s): {fields}.")

        cleaned = {}
        for field, value in data.items():
            if value is None or value == "":
                continue
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise ValueError(f"Entry {index} field '{field}' must be plain text.")
            cleaned[field] = str(value).strip()

        cleaned = {key: value for key, value in cleaned.items() if value}
        identity = (category, name.strip().casefold())
        if identity in seen:
            raise ValueError(f"Duplicate {category} entry in extraction: {name.strip()}.")
        seen.add(identity)
        records.append({
            "category": category,
            "name": name.strip(),
            "data": cleaned,
        })

    return records
