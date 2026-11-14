"""Transparent, rule-based story-structure recommendations.

This module provides creative guidance, not empirically validated predictions.
A genre affinity is a heuristic association, not a rule that a genre must use
a particular structure.
"""
import re

from story_structure import get_structure, get_structure_ids, list_structures


GENRE_ALIASES = {
    "sci fi": ("science_fiction",),
    "sci-fi": ("science_fiction",),
    "scifi": ("science_fiction",),
    "science fiction": ("science_fiction",),
    "psychological thriller": ("thriller", "psychological_drama"),
    "psychological drama": ("psychological_drama", "drama"),
    "romantic comedy": ("romance", "comedy"),
    "rom com": ("romance", "comedy"),
    "romcom": ("romance", "comedy"),
    "family film": ("family", "family_drama"),
    "historical": ("historical_drama",),
    "biopic": ("drama", "historical_drama"),
    "mythological": ("mythology", "fantasy"),
    "super hero": ("superhero",),
    "slice of life": ("slice_of_life",),
    "coming of age": ("coming_of_age",),
    "human interest": ("human_interest",),
    "action adventure": ("action", "adventure"),
    "disaster movie": ("disaster",),
}

EXPERIENCE_ALIASES = {
    "suspenseful": ("suspense",),
    "scary": ("dread",),
    "fear": ("dread",),
    "tension": ("tension",),
    "emotional": ("emotional_connection", "emotional_weight"),
    "emotional transformation": ("character_growth", "empathy"),
    "personal growth": ("character_growth",),
    "wonder and discovery": ("wonder", "discovery"),
    "thought provoking": ("moral_reflection", "contemplation"),
    "contemplative": ("contemplation", "observation"),
    "funny": ("comic_engagement",),
    "comedic": ("comic_engagement",),
    "commercially engaging": ("satisfaction", "momentum"),
    "spectacular": ("spectacle",),
}

ENGINE_ALIASES = {
    "escalating tension": "escalating_danger",
    "escalating crises": "escalating_danger",
    "crisis escalation": "escalating_danger",
    "downfall": "downfall_and_consequences",
    "consequences": "downfall_and_consequences",
    "character arc": "character_transformation",
    "personal transformation": "character_transformation",
    "commercial pacing": "commercial_pacing",
    "audience engagement": "commercial_pacing",
    "discovery": "discovery_and_contrast",
    "contrast": "discovery_and_contrast",
    "conflict": "conflict_and_resolution",
    "conflict resolution": "conflict_and_resolution",
    "journey": "extraordinary_journey",
    "hero journey": "extraordinary_journey",
    "hero s journey": "extraordinary_journey",
    "the hero s journey": "extraordinary_journey",
    "extraordinary journey": "extraordinary_journey",
    "character development": "character_transformation",
    "character transformation": "character_transformation",
}

ENGINE_LABELS = {
    "escalating_danger": "Escalating danger and crises",
    "downfall_and_consequences": "A protagonist's downfall and its consequences",
    "character_transformation": "Personal transformation",
    "commercial_pacing": "Commercial pacing and audience engagement",
    "discovery_and_contrast": "Discovery, contrast and observation",
    "conflict_and_resolution": "Conflict and resolution",
    "extraordinary_journey": "An extraordinary journey and transformation",
}

WEIGHTS = {
    "storytelling_engine": 5,
    "audience_experience": 3,
    "genre": 2,
}
MAX_SCORE = 5 + 6 + 4


def _normalise_text(value):
    text = str(value or "").strip().lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _as_values(value, field_name):
    if value is None:
        return []
    if isinstance(value, str):
        raw_values = re.split(r"[,;/\n]+", value)
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raise TypeError(f"{field_name} must be a string or a list/tuple/set of strings.")

    values = []
    for item in raw_values:
        if not isinstance(item, str):
            raise TypeError(f"Every {field_name} item must be a string.")
        item = item.strip()
        if item:
            values.append(item)
    return values


def _normalise_genres(values):
    result = set()
    for value in values:
        key = _normalise_text(value)
        alias = GENRE_ALIASES.get(key)
        if alias:
            result.update(alias)
        else:
            result.add(key.replace(" ", "_"))
    return result


def _normalise_experiences(values):
    result = set()
    for value in values:
        key = _normalise_text(value)
        alias = EXPERIENCE_ALIASES.get(key)
        if alias:
            result.update(alias)
        else:
            result.add(key.replace(" ", "_"))
    return result


def _normalise_engine(value):
    if not value:
        return None
    key = _normalise_text(value)
    if key in ENGINE_ALIASES:
        return ENGINE_ALIASES[key]
    return key.replace(" ", "_")


def recommend_structures(
    genre=None,
    audience_experience=None,
    storytelling_engine=None,
    limit=3,
):
    """Rank story structures with explainable, heuristic matches.

    Args:
        genre: Genre or genres, e.g. "psychological thriller" or ["horror", "crime"].
        audience_experience: Intended audience response, e.g. "dread", "wonder".
        storytelling_engine: Dominant dramatic engine, e.g. "escalating danger".
        limit: Maximum number of ranked recommendations (1 through 7).

    Returns:
        A dictionary with normalized input, ranked recommendations, and caveats.

    The recommendation score is a simple weighted heuristic: engine (5 points),
    audience-experience overlap (3 points each, capped at 6), and genre overlap
    (2 points each, capped at 4). Scores are not probabilities or research data.
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer from 1 to 7.")
    if not 1 <= limit <= len(get_structure_ids()):
        raise ValueError("limit must be between 1 and 7.")

    genres = _as_values(genre, "genre")
    experiences = _as_values(audience_experience, "audience_experience")
    if storytelling_engine is not None and not isinstance(storytelling_engine, str):
        raise TypeError("storytelling_engine must be a string.")
    engine = _normalise_engine(storytelling_engine)
    if engine and engine not in ENGINE_LABELS:
        choices = ", ".join(ENGINE_LABELS.values())
        raise ValueError(f"Unknown storytelling_engine. Choose one of: {choices}.")

    if not genres and not experiences and not engine:
        raise ValueError(
            "Provide at least one of genre, audience_experience, or storytelling_engine."
        )

    selected_genres = _normalise_genres(genres)
    selected_experiences = _normalise_experiences(experiences)
    results = []

    for structure in list_structures():
        reasons = []
        matched_genres = sorted(selected_genres.intersection(structure["best_for_genres"]))
        matched_experiences = sorted(
            selected_experiences.intersection(structure["audience_experiences"])
        )
        engine_match = engine == structure["primary_engine"] if engine else False

        genre_points = min(len(matched_genres) * WEIGHTS["genre"], 4)
        experience_points = min(
            len(matched_experiences) * WEIGHTS["audience_experience"], 6
        )
        engine_points = WEIGHTS["storytelling_engine"] if engine_match else 0
        score = genre_points + experience_points + engine_points

        if engine_match:
            reasons.append(
                f"Strong fit for the selected storytelling engine: "
                f"{ENGINE_LABELS.get(engine, engine.replace('_', ' '))}."
            )
        if matched_experiences:
            labels = ", ".join(item.replace("_", " ") for item in matched_experiences)
            reasons.append(f"Supports the intended audience experience: {labels}.")
        if matched_genres:
            labels = ", ".join(item.replace("_", " ") for item in matched_genres)
            reasons.append(f"Has a creative affinity with the selected genre: {labels}.")

        results.append({
            "structure_id": structure["id"],
            "name": structure["name"],
            "score": score,
            "max_score": MAX_SCORE,
            "score_breakdown": {
                "storytelling_engine": engine_points,
                "audience_experience": experience_points,
                "genre": genre_points,
            },
            "match_reasons": reasons,
            "strengths": structure["strengths"],
            "cautions": structure["cautions"],
            "components": structure["components"],
            "complements": structure["complements"],
        })

    results.sort(key=lambda item: (-item["score"], get_structure_ids().index(item["structure_id"])))
    matched = [item for item in results if item["score"] > 0]
    fallback_used = False
    if not matched:
        fallback_used = True
        fallback = next(item for item in results if item["structure_id"] == "three_act")
        fallback["match_reasons"] = [
            "No direct affinity was found for the supplied criteria. "
            "Three-Act is offered only as a flexible general-purpose starting point."
        ]
        fallback["fallback"] = True
        selected = [fallback]
    else:
        selected = matched[:limit]
        for item in selected:
            item["fallback"] = False

    return {
        "inputs": {
            "genre": genres,
            "audience_experience": experiences,
            "storytelling_engine": storytelling_engine,
        },
        "recommendations": selected,
        "fallback_used": fallback_used,
        "method": {
            "weights": dict(WEIGHTS),
            "maximum_score": MAX_SCORE,
            "note": (
                "Heuristic creative guidance only. Scores are not probabilities, "
                "measured film data, or proof that a genre requires a structure."
            ),
        },
    }


def get_complementary_structures(structure_id):
    """Return definitions for structures listed as useful complements."""
    structure = get_structure(structure_id)
    return [get_structure(item) for item in structure["complements"]]
