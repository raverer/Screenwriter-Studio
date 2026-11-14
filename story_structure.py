"""Structured knowledge library for the seven narrative frameworks.

Genre affinities are creative heuristics, not rules or empirically validated
genre-to-structure prescriptions. Film examples are illustrative comparisons,
not claims that the filmmakers formally used a named framework.
"""
from copy import deepcopy


STRUCTURE_ORDER = (
    "fichtean_curve",
    "freytags_pyramid",
    "story_circle",
    "save_the_cat",
    "kishotenketsu",
    "three_act",
    "monomyth",
)

_STRUCTURE_DATA = {
    "fichtean_curve": {
        "id": "fichtean_curve",
        "name": "Fichtean Curve",
        "core_principle": "Begin with a significant crisis and sustain momentum through escalating complications.",
        "primary_engine": "escalating_danger",
        "best_for_genres": [
            "thriller", "horror", "crime", "survival", "action", "disaster",
        ],
        "audience_experiences": ["suspense", "dread", "urgency", "tension"],
        "strengths": [
            "Creates an early reason for the audience to keep watching.",
            "Makes each crisis create pressure for the next.",
            "Limits long stretches of exposition when urgency is central.",
        ],
        "cautions": [
            "Continuous escalation can become exhausting without variation or meaningful relief.",
            "Less natural for stories built primarily on stillness, observation, or gradual discovery.",
        ],
        "components": [
            "Early crisis",
            "A series of escalating crises",
            "Brief periods of relief or exposition",
            "Climax",
            "Resolution",
        ],
        "complements": ["three_act", "story_circle"],
        "illustrative_films": ["Uncut Gems (2019)", "Good Time (2017)"],
        "example_note": "These films illustrate escalating-crisis patterns; this is not evidence that their screenwriters formally used the Fichtean Curve.",
    },
    "freytags_pyramid": {
        "id": "freytags_pyramid",
        "name": "Freytag's Pyramid",
        "core_principle": "Build dramatic tension toward a peak, then give substantial attention to consequences and denouement.",
        "primary_engine": "downfall_and_consequences",
        "best_for_genres": [
            "tragedy", "psychological_drama", "melodrama", "historical_drama",
            "crime", "social_drama", "drama",
        ],
        "audience_experiences": ["catharsis", "tragedy", "moral_reflection", "emotional_weight"],
        "strengths": [
            "Gives time to establish characters and circumstances before the dramatic peak.",
            "Makes consequences and aftermath an important part of the experience.",
            "Supports stories about ambition, moral compromise, downfall, and loss.",
        ],
        "cautions": [
            "Freytag developed the model primarily to analyse five-act dramatic works, especially tragedy.",
            "Its original placement of the climax differs from many modern screenplay formulas that place a major climax near the ending.",
        ],
        "components": [
            "Exposition",
            "Rising action",
            "Climax",
            "Falling action",
            "Denouement or catastrophe",
        ],
        "complements": ["three_act", "story_circle"],
        "illustrative_films": ["There Will Be Blood (2007)", "The Godfather (1972)"],
        "example_note": "These films are illustrative comparisons for dramatic rise and consequences, not proof of formal use of Freytag's model.",
    },
    "story_circle": {
        "id": "story_circle",
        "name": "Dan Harmon's Story Circle",
        "core_principle": "A character leaves a familiar situation, adapts to an unfamiliar one, pays a price, and returns changed.",
        "primary_engine": "character_transformation",
        "best_for_genres": [
            "comedy", "adventure", "coming_of_age", "romance", "fantasy",
            "character_drama", "drama",
        ],
        "audience_experiences": ["empathy", "character_growth", "comic_engagement", "emotional_connection"],
        "strengths": [
            "Connects external events to a protagonist's internal need and transformation.",
            "Provides a compact, repeatable shape for episodic stories.",
            "Can support stories in which the journey matters as much as the destination.",
        ],
        "cautions": [
            "The return-and-change pattern may feel artificial for stories whose protagonists do not return to a familiar situation.",
            "A circle is a character-journey lens, not a substitute for every scene-level plotting decision.",
        ],
        "components": [
            "You",
            "Need",
            "Go",
            "Search",
            "Find",
            "Take",
            "Return",
            "Change",
        ],
        "complements": ["three_act", "save_the_cat", "monomyth"],
        "illustrative_films": ["Groundhog Day (1993)", "Finding Nemo (2003)"],
        "example_note": "These films illustrate character-change journeys; the comparison does not establish formal use of Harmon's framework.",
    },
    "save_the_cat": {
        "id": "save_the_cat",
        "name": "Save the Cat",
        "core_principle": "Shape audience engagement and pacing through a sequence of deliberately placed story beats.",
        "primary_engine": "commercial_pacing",
        "best_for_genres": [
            "comedy", "romance", "action", "family", "adventure",
            "superhero", "science_fiction", "drama",
        ],
        "audience_experiences": [
            "satisfaction", "comic_engagement", "emotional_connection",
            "spectacle", "momentum",
        ],
        "strengths": [
            "Provides a practical beat sheet for planning and diagnosing a commercial screenplay.",
            "Makes pacing, reversals, emotional setbacks, and payoff explicit.",
            "Can help writers communicate story progression in a shared production vocabulary.",
        ],
        "cautions": [
            "Its prescriptive beat placement can feel formulaic when followed mechanically.",
            "It is a practical screenwriting framework, not an empirically established universal law.",
        ],
        "components": [
            "Opening Image",
            "Theme Stated",
            "Set-Up",
            "Catalyst",
            "Debate",
            "Break into Two",
            "B Story",
            "Fun and Games",
            "Midpoint",
            "Bad Guys Close In",
            "All Is Lost",
            "Dark Night of the Soul",
            "Break into Three",
            "Finale",
            "Final Image",
        ],
        "complements": ["story_circle", "three_act"],
        "illustrative_films": ["Legally Blonde (2001)", "The Martian (2015)"],
        "example_note": "These are illustrative commercial-storytelling comparisons, not verified beat-by-beat analyses.",
    },
    "kishotenketsu": {
        "id": "kishotenketsu",
        "name": "Kishōtenketsu",
        "core_principle": "Create meaning through introduction, development, contrast or twist, and a conclusion that connects the elements.",
        "primary_engine": "discovery_and_contrast",
        "best_for_genres": [
            "slice_of_life", "family_drama", "coming_of_age", "contemplative",
            "magical_realism", "animation", "human_interest", "drama",
        ],
        "audience_experiences": ["discovery", "contemplation", "wonder", "observation", "emotional_subtlety"],
        "strengths": [
            "Can generate interest through contrast and a changed perspective rather than direct confrontation.",
            "Supports observational, everyday, and contemplative stories.",
            "Allows juxtaposition to create emotional or thematic meaning.",
        ],
        "cautions": [
            "It does not require a conventional protagonist-versus-antagonist conflict.",
            "It should not be treated as the defining structure of all East Asian cinema.",
        ],
        "components": [
            "Ki — Introduction",
            "Shō — Development",
            "Ten — Twist or contrast",
            "Ketsu — Conclusion or connection",
        ],
        "complements": ["story_circle", "three_act"],
        "illustrative_films": ["My Neighbor Totoro (1988)", "Perfect Days (2023)"],
        "example_note": "These films are illustrative comparisons for observation and discovery, not proof of formal use of Kishōtenketsu.",
    },
    "three_act": {
        "id": "three_act",
        "name": "Three-Act Structure",
        "core_principle": "Establish a situation, complicate it through confrontation, and bring the central conflict to a resolution.",
        "primary_engine": "conflict_and_resolution",
        "best_for_genres": [
            "thriller", "horror", "crime", "survival", "action", "disaster",
            "tragedy", "psychological_drama", "melodrama", "historical_drama",
            "social_drama", "comedy", "adventure", "coming_of_age", "romance",
            "fantasy", "family", "family_drama", "slice_of_life",
            "magical_realism", "animation", "science_fiction", "superhero",
            "mythology", "epic", "drama", "human_interest",
        ],
        "audience_experiences": [
            "suspense", "dread", "catharsis", "empathy", "satisfaction",
            "wonder", "discovery", "comic_engagement", "emotional_connection",
            "character_growth", "momentum",
        ],
        "strengths": [
            "Provides a flexible overall backbone for setup, confrontation, and resolution.",
            "Supports cause-and-effect progression, subplots, and multiple genres.",
            "Can act as a high-level container for more specialised structures or beat systems.",
        ],
        "cautions": [
            "The three-act model is a broad organising framework, not a fixed beat sheet.",
            "Act divisions and turning points vary across screenwriting traditions and individual films.",
        ],
        "components": [
            "Act I — Setup",
            "Act II — Confrontation",
            "Act III — Resolution",
        ],
        "complements": ["fichtean_curve", "freytags_pyramid", "story_circle", "save_the_cat", "monomyth"],
        "illustrative_films": ["The Dark Knight (2008)", "The Pursuit of Happyness (2006)"],
        "example_note": "These films are illustrative examples of conventional conflict progression, not proof of a single formal act breakdown.",
    },
    "monomyth": {
        "id": "monomyth",
        "name": "The Monomyth / Hero's Journey",
        "core_principle": "A protagonist enters an unfamiliar world, faces tests and an ordeal, and returns transformed.",
        "primary_engine": "extraordinary_journey",
        "best_for_genres": [
            "fantasy", "mythology", "science_fiction", "adventure",
            "superhero", "epic", "coming_of_age",
        ],
        "audience_experiences": ["wonder", "spectacle", "character_growth", "inspiration", "adventure"],
        "strengths": [
            "Connects external adventure with internal transformation.",
            "Offers a useful vocabulary for journeys, tests, mentors, ordeals, sacrifice, and return.",
            "Supports mythic scale, world-building, and symbolic storytelling.",
        ],
        "cautions": [
            "The model should not be imposed on every protagonist or every cultural tradition.",
            "Campbell's comparative account and Vogler's practical 12-stage adaptation are related but not identical.",
        ],
        "components": [
            "Ordinary World",
            "Call to Adventure",
            "Refusal of the Call",
            "Meeting the Mentor",
            "Crossing the Threshold",
            "Tests, Allies and Enemies",
            "Approach to the Inmost Cave",
            "Ordeal",
            "Reward",
            "The Road Back",
            "Resurrection",
            "Return with the Elixir",
        ],
        "complements": ["three_act", "story_circle", "save_the_cat"],
        "illustrative_films": ["Star Wars: A New Hope (1977)", "The Lord of the Rings: The Fellowship of the Ring (2001)"],
        "example_note": "These are widely used illustrative Hero's Journey comparisons; do not infer that every stage maps exactly.",
    },
}


def list_structures():
    """Return all seven structure definitions in a stable, documented order."""
    return [deepcopy(_STRUCTURE_DATA[key]) for key in STRUCTURE_ORDER]


def get_structure(structure_id):
    """Return a copy of one structure definition by its stable ID."""
    key = str(structure_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key not in _STRUCTURE_DATA:
        valid = ", ".join(STRUCTURE_ORDER)
        raise ValueError(f"Unknown story structure '{structure_id}'. Choose one of: {valid}.")
    return deepcopy(_STRUCTURE_DATA[key])


def get_structure_ids():
    """Return the stable IDs for all supported structures."""
    return list(STRUCTURE_ORDER)
