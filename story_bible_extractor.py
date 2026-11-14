"""Structured extraction of Story Bible candidates from screenplay text."""
import json

from story_bible import list_entries, upsert_entry

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
Do not create entries for incidental objects unless they matter to the story.

Return ONLY a JSON object with this structure:
{{"entries": [{{"category": "one exact category", "name": "entity name", "data": {{}}}}]}}

For each entry choose exactly one category: character, location, prop, or timeline.

Allowed category-specific data fields:
- character: age, occupation_or_role, personality, goal_motivation, relationships, continuity_notes
- location: place_type, description, atmosphere_time, key_details
- prop: description, owner_custodian, story_significance, continuity_notes
- timeline: when, event, characters_involved, consequences

Use only the fields allowed for that category. Do not copy placeholder text.
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
        if not isinstance(category, str) or category not in FIELD_SCHEMAS:
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



def save_extracted_entries(project_id, records, allow_overwrite=False, db_path=None):
    """Persist reviewed candidates, refusing name collisions unless approved.

    Returns counts for created and updated records. The caller must invoke this
    only after the user explicitly approves the reviewed extraction.
    """
    if project_id is None:
        raise ValueError("A project must be selected before saving Story Bible entries.")
    if not isinstance(records, list):
        raise ValueError("Extraction records must be a list.")

    existing = list_entries(project_id, db_path=db_path)
    existing_by_key = {
        (item["category"], item["name"].strip().casefold()): item
        for item in existing
    }
    conflicts = [
        record for record in records
        if (record["category"], record["name"].strip().casefold()) in existing_by_key
    ]
    if conflicts and not allow_overwrite:
        names = ", ".join(item["name"] for item in conflicts)
        raise ValueError(
            "Existing Story Bible entries would be updated: "
            + names
            + ". Explicitly approve updating matching records to continue."
        )

    created = 0
    updated = 0
    for record in records:
        key = (record["category"], record["name"].strip().casefold())
        match = existing_by_key.get(key)
        if match:
            upsert_entry(
                project_id,
                record["category"],
                record["name"],
                record["data"],
                entry_id=match["id"],
                db_path=db_path,
            )
            updated += 1
        else:
            upsert_entry(
                project_id,
                record["category"],
                record["name"],
                record["data"],
                db_path=db_path,
            )
            created += 1
    return {"created": created, "updated": updated}
