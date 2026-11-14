"""Generate and validate story-wide architecture blueprints.

The LLM proposes creative story events. This module validates the structure and
shape of the proposal before a caller presents it for writer review. It does not
claim that a generated outline is dramatically effective or objectively correct.
"""
import json
from collections.abc import Mapping

from story_structure import get_structure


TOP_LEVEL_FIELDS = (
    "structure_id",
    "title",
    "dramatic_question",
    "theme",
    "protagonist_arc",
    "central_conflict",
    "stakes",
    "ending_type",
    "beats",
)
ARC_FIELDS = (
    "starting_state",
    "external_goal",
    "internal_need",
    "ending_state",
)
BEAT_FIELDS = (
    "component",
    "story_event",
    "dramatic_function",
    "cause_and_effect",
    "protagonist_shift",
    "open_questions",
)
DEFAULT_MAX_BEAT_QUESTIONS = 4


def build_architecture_system_prompt():
    """Return system instructions for a screenplay story architect."""
    return (
        "You are an experienced screenwriter and story editor. Build coherent, "
        "specific, filmable story architecture from the writer's project brief. "
        "Respect the selected narrative framework's mechanics and exact component "
        "sequence. Do not present generic advice instead of concrete story events. "
        "Do not claim that any structure is mandatory for a genre. Return only "
        "valid JSON matching the requested schema."
    )


def _normalise_project_details(project_details):
    if project_details is None:
        return {}
    if not isinstance(project_details, Mapping):
        raise TypeError("project_details must be a dictionary-like mapping.")

    allowed_fields = (
        "title",
        "format",
        "language",
        "genre",
        "tone",
        "logline",
        "characters",
        "setting",
        "notes",
        "writing_style",
        "audience_guidance",
    )
    result = {}
    for field in allowed_fields:
        value = project_details.get(field, "")
        if value is None:
            value = ""
        if not isinstance(value, (str, int, float, list, tuple)):
            raise TypeError(f"Project detail '{field}' must be text or a list of text.")
        if isinstance(value, (list, tuple)):
            if not all(isinstance(item, str) for item in value):
                raise TypeError(f"Every item in project detail '{field}' must be text.")
            value = list(value)
        else:
            value = str(value).strip()
        if value != "" and value != []:
            result[field] = value
    return result


def build_architecture_prompt(structure_id, project_details=None):
    """Build a JSON-only blueprint prompt for one selected story structure."""
    structure = get_structure(structure_id)
    details = _normalise_project_details(project_details)

    components_json = json.dumps(structure["components"], ensure_ascii=False)
    details_json = json.dumps(details, ensure_ascii=False, indent=2)
    schema = {
        "structure_id": structure["id"],
        "title": "string",
        "dramatic_question": "string",
        "theme": "string",
        "protagonist_arc": {
            "starting_state": "string",
            "external_goal": "string",
            "internal_need": "string",
            "ending_state": "string",
        },
        "central_conflict": "string",
        "stakes": "string",
        "ending_type": "string",
        "beats": [
            {
                "component": "one exact component label from the supplied ordered list",
                "story_event": "specific event in this story",
                "dramatic_function": "what this part accomplishes",
                "cause_and_effect": "how it follows from or causes another event",
                "protagonist_shift": "what changes for the protagonist",
                "open_questions": ["optional question for the writer"],
            }
        ],
    }

    return f"""Create a complete story-wide architecture blueprint for this screenplay project.

SELECTED STRUCTURE
Name: {structure["name"]}
Core principle: {structure["core_principle"]}
Primary storytelling engine: {structure["primary_engine"]}
Cautions to respect:
{chr(10).join("- " + item for item in structure["cautions"])}

The structure's components are fixed and must appear exactly once, in this exact order.
Do not rename, merge, omit, reorder, or add components:
{components_json}

PROJECT BRIEF
{details_json if details else "{}"}

TASK
Propose a coherent story architecture that uses the selected structure as its
primary organising framework. Respect the project's genre, tone, format, language,
characters, setting and premise. Do not invent facts that contradict the brief.
Where the brief leaves creative gaps, make clearly plausible story choices rather
than returning generic placeholders.

For every component, write a specific story event for THIS project, explain its
dramatic function, connect it causally to the surrounding events, and state how
the protagonist changes or responds. Distinguish external goal from internal need.
Make stakes concrete. Ensure the ending answers or deliberately reframes the
dramatic question.

Treat the framework as a creative planning tool, not a rigid law. In particular:
- Fichtean Curve: crises should escalate, vary, and create new consequences.
- Freytag's Pyramid: include meaningful rising action and consequences after the peak.
- Story Circle: connect the external journey to an internal need and changed return.
- Save the Cat: include all 15 named beats in the supplied order; avoid generic beat labels.
- Kishōtenketsu: make the contrast/twist change the audience's understanding; do not force a conventional antagonist conflict.
- Three-Act: define setup, confrontation and resolution at the macro-story level.
- Monomyth: make the journey and ordeal specific to this protagonist; do not force culturally inappropriate stages.

OUTPUT RULES
Return ONLY one valid JSON object. No Markdown fences or explanation.
Use this exact top-level shape and field names:
{json.dumps(schema, ensure_ascii=False, indent=2)}

The "structure_id" must be exactly "{structure["id"]}".
"beats" must contain exactly {len(structure["components"])} items.
Every beat's "component" must exactly match the corresponding item in the supplied list.
All required values must be specific, concise strings, not empty placeholders.
"open_questions" must be a JSON array of zero to {DEFAULT_MAX_BEAT_QUESTIONS} short strings.
"""


def _extract_json_object(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("The model returned an empty story architecture response.")
    text = raw.strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("The model did not return a JSON object.")
    try:
        payload = json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid story architecture JSON: {exc.msg}. Generate the blueprint again."
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("Story architecture response must be a JSON object.")
    return payload


def _require_text(value, field_path):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field_path}' must be a non-empty string.")
    return value.strip()


def validate_architecture(architecture, structure_id):
    """Validate required story fields and exact structure beat coverage.

    Returns a normalized copy. Raises ValueError for invalid content and never
    saves anything to the database.
    """
    structure = get_structure(structure_id)
    if not isinstance(architecture, Mapping):
        raise TypeError("Architecture must be a dictionary-like mapping.")

    missing = [field for field in TOP_LEVEL_FIELDS if field not in architecture]
    if missing:
        raise ValueError(f"Architecture is missing required fields: {', '.join(missing)}.")

    actual_id = architecture.get("structure_id")
    if actual_id != structure["id"]:
        raise ValueError(
            f"Blueprint structure_id must be '{structure['id']}', got {actual_id!r}."
        )

    normalized = {
        "structure_id": structure["id"],
        "title": _require_text(architecture["title"], "title"),
        "dramatic_question": _require_text(
            architecture["dramatic_question"], "dramatic_question"
        ),
        "theme": _require_text(architecture["theme"], "theme"),
        "central_conflict": _require_text(
            architecture["central_conflict"], "central_conflict"
        ),
        "stakes": _require_text(architecture["stakes"], "stakes"),
        "ending_type": _require_text(architecture["ending_type"], "ending_type"),
    }

    arc = architecture["protagonist_arc"]
    if not isinstance(arc, Mapping):
        raise ValueError("'protagonist_arc' must be an object.")
    missing_arc = [field for field in ARC_FIELDS if field not in arc]
    if missing_arc:
        raise ValueError(
            "protagonist_arc is missing required fields: " + ", ".join(missing_arc) + "."
        )
    normalized["protagonist_arc"] = {
        field: _require_text(arc[field], f"protagonist_arc.{field}")
        for field in ARC_FIELDS
    }

    beats = architecture["beats"]
    if not isinstance(beats, list):
        raise ValueError("'beats' must be an array.")
    expected_components = structure["components"]
    if len(beats) != len(expected_components):
        raise ValueError(
            f"'{structure['name']}' requires exactly {len(expected_components)} beats; "
            f"received {len(beats)}."
        )

    normalized_beats = []
    for index, (beat, expected_component) in enumerate(
        zip(beats, expected_components), start=1
    ):
        if not isinstance(beat, Mapping):
            raise ValueError(f"Beat {index} must be an object.")
        missing_beat = [field for field in BEAT_FIELDS if field not in beat]
        if missing_beat:
            raise ValueError(
                f"Beat {index} is missing fields: {', '.join(missing_beat)}."
            )
        component = _require_text(beat["component"], f"beats[{index - 1}].component")
        if component != expected_component:
            raise ValueError(
                f"Beat {index} must be '{expected_component}' in the selected order; "
                f"received '{component}'."
            )

        questions = beat["open_questions"]
        if not isinstance(questions, list):
            raise ValueError(f"Beat {index} open_questions must be an array.")
        if len(questions) > DEFAULT_MAX_BEAT_QUESTIONS:
            raise ValueError(
                f"Beat {index} can contain at most {DEFAULT_MAX_BEAT_QUESTIONS} open questions."
            )
        cleaned_questions = [
            _require_text(question, f"beats[{index - 1}].open_questions[{q_index}]")
            for q_index, question in enumerate(questions)
        ]

        normalized_beats.append({
            "component": component,
            "story_event": _require_text(
                beat["story_event"], f"beats[{index - 1}].story_event"
            ),
            "dramatic_function": _require_text(
                beat["dramatic_function"], f"beats[{index - 1}].dramatic_function"
            ),
            "cause_and_effect": _require_text(
                beat["cause_and_effect"], f"beats[{index - 1}].cause_and_effect"
            ),
            "protagonist_shift": _require_text(
                beat["protagonist_shift"], f"beats[{index - 1}].protagonist_shift"
            ),
            "open_questions": cleaned_questions,
        })

    normalized["beats"] = normalized_beats
    return normalized


def parse_architecture_response(raw, structure_id):
    """Parse a model response and validate it for the selected framework."""
    return validate_architecture(_extract_json_object(raw), structure_id)


def format_architecture_context(architecture):
    """Convert an approved architecture into compact prompt context.

    The caller should pass a writer-reviewed and approved architecture.
    """
    if not isinstance(architecture, Mapping):
        raise TypeError("Architecture must be a dictionary-like mapping.")
    structure = get_structure(architecture.get("structure_id"))
    checked = validate_architecture(architecture, structure["id"])
    lines = [
        "APPROVED STORY ARCHITECTURE",
        f"Primary structure: {structure['name']}",
        f"Title: {checked['title']}",
        f"Dramatic question: {checked['dramatic_question']}",
        f"Theme: {checked['theme']}",
        f"Central conflict: {checked['central_conflict']}",
        f"Stakes: {checked['stakes']}",
        f"Ending type: {checked['ending_type']}",
        "Protagonist arc:",
        f"- Starting state: {checked['protagonist_arc']['starting_state']}",
        f"- External goal: {checked['protagonist_arc']['external_goal']}",
        f"- Internal need: {checked['protagonist_arc']['internal_need']}",
        f"- Ending state: {checked['protagonist_arc']['ending_state']}",
        "Structural progression:",
    ]
    for index, beat in enumerate(checked["beats"], start=1):
        lines.append(
            f"{index}. {beat['component']}: {beat['story_event']} "
            f"(Function: {beat['dramatic_function']}; "
            f"Cause/effect: {beat['cause_and_effect']}; "
            f"Protagonist shift: {beat['protagonist_shift']})"
        )
    lines.append(
        "Keep future scenes consistent with this approved architecture. "
        "Do not force a beat into a scene if it would damage causality; "
        "flag a potential structural conflict for writer review."
    )
    return "\n".join(lines)
