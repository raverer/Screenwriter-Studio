"""Evidence-based LLM evaluation of a screenplay scene against its blueprint."""
import json
import re

CRITERIA = [
    "blueprint_adherence",
    "character_consistency",
    "dramatic_conflict",
    "beat_progression",
    "genre_and_tone",
    "visual_storytelling",
    "ending_hook",
]


def build_evaluation_prompt(blueprint, screenplay):
    return f"""Evaluate the screenplay against the approved scene blueprint.
Be a rigorous but constructive script editor. Score each criterion from 1 to 5:
1 = absent/poor, 2 = weak, 3 = partly achieved, 4 = strong, 5 = excellent.
Do not reward the blueprint for merely mentioning an intention: assess what is
actually present in the screenplay. Every criterion must include a short,
verbatim evidence excerpt from the screenplay. If no evidence exists, use an
empty evidence string and explain the gap. Do not invent quotations.

Return ONLY valid JSON with this exact structure:
{{
  "criteria": {{
    "blueprint_adherence": {{"score": 1, "evidence": "exact excerpt", "feedback": "explanation"}},
    "character_consistency": {{"score": 1, "evidence": "exact excerpt", "feedback": "explanation"}},
    "dramatic_conflict": {{"score": 1, "evidence": "exact excerpt", "feedback": "explanation"}},
    "beat_progression": {{"score": 1, "evidence": "exact excerpt", "feedback": "explanation"}},
    "genre_and_tone": {{"score": 1, "evidence": "exact excerpt", "feedback": "explanation"}},
    "visual_storytelling": {{"score": 1, "evidence": "exact excerpt", "feedback": "explanation"}},
    "ending_hook": {{"score": 1, "evidence": "exact excerpt", "feedback": "explanation"}}
  }},
  "strengths": ["specific strength"],
  "improvements": ["specific actionable improvement"],
  "overall_assessment": "brief balanced assessment"
}}

APPROVED BLUEPRINT:
{blueprint[:9000]}

SCREENPLAY:
{screenplay[:16000]}"""


def _extract_json(raw):
    text = raw.strip()
    text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text, flags=re.IGNORECASE)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Evaluator did not return valid JSON: no JSON object was found.")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Evaluator returned invalid JSON: {exc.msg}. Try evaluating again.") from exc


def _normalise_evidence(value):
    """Normalise punctuation, typography and whitespace for evidence matching."""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = value.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.casefold().split())

def evaluate_scene(blueprint, screenplay, llm_call):
    """Call an injected LLM function and validate the structured evaluation."""
    if not blueprint or not blueprint.strip():
        raise ValueError("An approved scene blueprint is required for evaluation.")
    if not screenplay or not screenplay.strip():
        raise ValueError("A screenplay is required for evaluation.")

    raw = llm_call(
        "You are a rigorous screenplay evaluator. Follow the requested JSON schema exactly. Evidence must be quoted verbatim from the screenplay.",
        build_evaluation_prompt(blueprint, screenplay),
    )
    data = _extract_json(raw)
    criteria = data.get("criteria")
    if not isinstance(criteria, dict):
        raise ValueError("Evaluation JSON is missing the criteria object.")

    validated = {}
    for name in CRITERIA:
        item = criteria.get(name)
        if not isinstance(item, dict):
            raise ValueError(f"Evaluation is missing criterion: {name}.")
        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
            raise ValueError(f"Invalid score for {name}; expected an integer from 1 to 5.")
        evidence = item.get("evidence", "")
        feedback = item.get("feedback", "")
        if not isinstance(evidence, str) or not isinstance(feedback, str):
            raise ValueError(f"Evidence and feedback for {name} must be text.")
        if evidence and _normalise_evidence(evidence) not in _normalise_evidence(screenplay):
            evidence = ""
            feedback = feedback.rstrip() + " [The supplied evidence could not be verified against the screenplay and has been omitted.]"
        validated[name] = {"score": score, "evidence": evidence, "feedback": feedback}

    normalised_lists = {}
    for field in ("strengths", "improvements"):
        value = data.get(field, [])
        if value is None:
            value = []
        elif isinstance(value, str):
            value = [value]
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise ValueError(f"Evaluation field '{field}' must contain text or a list of text.")
        normalised_lists[field] = [item.strip() for item in value if item.strip()]

    if not isinstance(data.get("overall_assessment"), str):
        raise ValueError("Evaluation is missing its overall_assessment text.")

    average = round(sum(item["score"] for item in validated.values()) / len(validated), 2)
    return {
        "criteria": validated,
        "average_score": average,
        "strengths": normalised_lists["strengths"],
        "improvements": normalised_lists["improvements"],
        "overall_assessment": data["overall_assessment"],
    }
