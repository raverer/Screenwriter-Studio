# Story Structure Knowledge Library and Recommender

## Purpose

Phase 1 adds a deterministic knowledge layer for seven narrative frameworks. It is designed to support later Story Architecture Blueprint generation and structure-aware scene planning.

The library is reference data; the recommender is a transparent heuristic. Neither claims that a genre must use one structure or that a score predicts audience response, commercial success, or artistic quality.

## Supported frameworks

The stable identifiers are:

- `fichtean_curve`
- `freytags_pyramid`
- `story_circle`
- `save_the_cat`
- `kishotenketsu`
- `three_act`
- `monomyth`

Each definition contains a core principle, primary storytelling engine, genre affinities, audience experiences, strengths, cautions, structural components, complementary structures, and illustrative film comparisons.

Film examples are labelled as illustrative comparisons. A film's resemblance to a structure does not prove that its writers formally used that framework.

## Recommendation inputs

The deterministic recommender accepts three optional criteria. At least one must be supplied.

| Input | Examples | Purpose |
|---|---|---|
| Genre | `horror`, `psychological thriller`, `romantic comedy` | Finds structures with a creative affinity for the genre |
| Audience experience | `dread`, `suspense`, `wonder`, `character growth` | Finds structures that support the intended response |
| Storytelling engine | `escalating danger`, `character transformation`, `discovery and contrast` | Identifies the dominant mechanism driving the story |

Genre aliases normalize common variations such as `sci-fi`, `slice-of-life`, `coming-of-age`, and `rom-com`. Audience-experience aliases normalize common descriptions such as `scary`, `funny`, and `contemplative`.

## Scoring method

The score is a simple ranking heuristic with a maximum of 15 points:

| Signal | Points |
|---|---:|
| Exact storytelling-engine match | 5 |
| Each matched audience-experience tag | 3, capped at 6 |
| Each matched genre-affinity tag | 2, capped at 4 |

The formula is:

`score = engine_points + audience_points + genre_points`

The recommender returns the score breakdown, matched reasons, framework strengths, cautions, and complementary structure IDs. Ties follow the stable structure-library order.

The score is not a probability, confidence estimate, empirical statistic, or quality rating. It must be presented to writers as heuristic creative guidance.

If none of the supplied criteria match a framework, the recommender returns Three-Act Structure as an explicitly labelled general-purpose fallback. This is not reported as a positive genre match.

## Story Architecture Blueprint generation

The Streamlit app now includes a Story Architecture section for an active project.

1. The writer chooses intended audience experiences and a dominant storytelling engine.
2. The app shows the top heuristic structure recommendations based on those choices and the project's genre.
3. The writer selects a primary structure, including the option to override the recommendation.
4. Ollama generates a story-wide blueprint using that structure's exact component sequence.
5. The writer can edit the JSON blueprint.
6. The application validates the structure ID, required story fields, beat count, and exact component order before approval.

The common blueprint schema contains:

- Story title, dramatic question, theme, central conflict, stakes and ending type.
- Protagonist starting state, external goal, internal need and ending state.
- One beat object per component, containing its story event, dramatic function, cause-and-effect link, protagonist shift and optional open questions.

The component sequences remain structure-specific: for example, Save the Cat requires 15 beats, Kishōtenketsu requires four, and the Monomyth uses the 12 stages defined in the library.

The LLM call is injected into `generate_architecture()`, so parsing and validation can be unit-tested with a fake model response without requiring Ollama in CI. Malformed or incomplete model output is rejected rather than silently approved.

**Current boundary:** a writer-approved architecture is held in Streamlit session state only. It is not yet persisted to SQLite or automatically included in Scene Blueprint and screenplay-generation prompts. The next phase is project-scoped persistence and safe workspace restoration.

## Python usage

```python
from structure_recommender import recommend_structures

result = recommend_structures(
    genre="psychological thriller",
    audience_experience=["suspense", "dread"],
    storytelling_engine="escalating danger",
    limit=3,
)

for item in result["recommendations"]:
    print(item["name"], item["score"], item["match_reasons"])
```

The result also contains:

- `inputs`: the user's original criteria.
- `recommendations`: ranked options and explanations.
- `fallback_used`: whether the general-purpose fallback was required.
- `method`: weights, maximum score, and a caveat about heuristic use.

The library can be accessed with `list_structures()`, `get_structure(id)`, and `get_structure_ids()` from `story_structure.py`. Returned structure definitions are copies, so callers cannot mutate the shared library accidentally.

## Tests

Run the focused tests:

```bash
python -m unittest discover -s tests -p "test_story_structure.py" -v
```

Run the full suite:

```bash
python -m unittest discover -s tests -v
```

## Research limitations

The genre affinities are based on narrative-mechanics reasoning and the creative mapping in the initial research brief. They are not a validated dataset. The research discussed in the brief suggests that narrative patterns and genres may be associated, but does not establish a universal best structure by genre.

A future film-mapping study should record observed beats, sequence positions, and supporting scene evidence. It should distinguish formal use of a framework from retrospective resemblance, and should not train or calibrate this rule-based recommender until its sampling and annotation method has been validated.
