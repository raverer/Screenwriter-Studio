"""Duration rules and prompt guidance for supported screenplay formats."""

FORMAT_OPTIONS = (
    "Feature Film",
    "OTT / Web Series",
    "Short Film",
    "Advertisement",
    "TVC",
    "Micro Drama",
)

DURATION_RANGES = {
    "Advertisement": (15, 120),
    "TVC": (15, 120),
    "Micro Drama": (150, 200),
}
DEFAULT_DURATIONS = {
    "Advertisement": 30,
    "TVC": 30,
    "Micro Drama": 180,
}


def is_compact_script_format(project_type):
    """Whether the format is drafted as one complete, short-form script."""
    return project_type in DURATION_RANGES


def get_duration_range(project_type):
    """Return the allowed (minimum, maximum) runtime, or None if unrestricted."""
    return DURATION_RANGES.get(project_type)


def validate_target_duration(project_type, duration_seconds):
    """Validate a selected runtime against the selected format."""
    limits = get_duration_range(project_type)
    if limits is None:
        return None
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int):
        raise ValueError("Target runtime must be a whole number of seconds.")
    minimum, maximum = limits
    if not minimum <= duration_seconds <= maximum:
        raise ValueError(
            f"{project_type} runtime must be between {minimum} and {maximum} seconds."
        )
    return duration_seconds


def build_format_guidance(project_type, duration_seconds=None):
    """Return prompt instructions specific to the selected screenplay format."""
    if project_type not in FORMAT_OPTIONS:
        raise ValueError(f"Unsupported screenplay format: {project_type}")
    if not is_compact_script_format(project_type):
        return (
            f"FORMAT GUIDANCE: Write for {project_type}. Use an appropriate "
            "dramatic scale, pacing and screenplay convention for this format."
        )

    duration = validate_target_duration(project_type, duration_seconds)
    timing = (
        f"TARGET RUNTIME: {duration} seconds. Treat this as the requested finished "
        "screen duration, not an approximate word count. Build a timed sequence "
        "whose segment timings add up to the target runtime. Do not exceed or "
        "fall short of it. Avoid padding and allow time for performance, pauses, "
        "visual action, transitions, supers and end card."
    )

    if project_type in {"Advertisement", "TVC"}:
        kind = "advertisement" if project_type == "Advertisement" else "television commercial (TVC)"
        return "\n".join([
            f"FORMAT: {project_type} ({kind}).",
            "Write one complete, shootable commercial script, not a feature-film scene.",
            timing,
            "Use a clear timed shot/scene sequence with visual action, dialogue or voice-over, "
            "sound/music and on-screen supers where useful.",
            "Establish the audience hook quickly, communicate one clear product/brand "
            "proposition, demonstrate or dramatize its benefit, deliver a memorable "
            "brand moment and finish with a clear call to action when appropriate.",
            "Do not invent product features, performance claims, prices, offers, "
            "endorsements or legal copy. Use placeholders when the brief has not supplied them.",
            "Keep the storytelling focused; do not add subplots or scenes that do not "
            "serve the commercial message.",
        ])

    return "\n".join([
        "FORMAT: Micro Drama.",
        "Write one complete, self-contained micro-drama script, not a feature-film scene "
        "or a multi-episode outline.",
        timing,
        "Open with an immediate dramatic hook. Give the protagonist a clear objective, "
        "build one central conflict, escalate it through a small number of timed scenes, "
        "and deliver a satisfying payoff or a strong final reversal/cliffhanger.",
        "Use economical locations and cast where possible, but do not sacrifice character "
        "motivation, emotional clarity or cause-and-effect.",
        "Use screenplay scene headings, concise action and playable dialogue. Avoid "
        "advertising-style product pitches unless the writer's brief calls for one.",
    ])


def build_compact_blueprint_task(project_type, duration_seconds):
    """Return a full-script planning task for Advertisement, TVC or Micro Drama."""
    validate_target_duration(project_type, duration_seconds)
    if project_type in {"Advertisement", "TVC"}:
        return (
            f"Plan the COMPLETE {project_type} script for exactly {duration_seconds} seconds. "
            "Do not plan only an opening scene. Map the full commercial from its first frame "
            "to its final brand moment/end card, using timed shots or scenes whose durations "
            "sum to the target runtime."
        )
    return (
        f"Plan the COMPLETE Micro Drama for exactly {duration_seconds} seconds. "
        "Do not plan only an opening scene or a multi-episode series. Map the full dramatic "
        "arc from hook through escalating conflict to its payoff or final reversal, using "
        "timed scenes whose durations sum to the target runtime."
    )


def build_compact_blueprint_sections(project_type):
    """Return the planning fields expected for compact complete-script formats."""
    if project_type in {"Advertisement", "TVC"}:
        return """COMMERCIAL IDEA:
CORE AUDIENCE:
PRODUCT / BRAND:
SINGLE-MINDED MESSAGE:
KEY BENEFIT (only if supplied in the brief):
CALL TO ACTION:
TOTAL RUNTIME:
TIMED SHOT / SCENE BREAKDOWN (start-end time, visual, audio/VO/dialogue, supers, purpose):
BRAND REVEAL / END CARD:
PRODUCTION CONSIDERATIONS:
OPEN QUESTIONS / UNSUPPLIED CLAIMS:"""
    if project_type == "Micro Drama":
        return """DRAMATIC HOOK:
PROTAGONIST AND OBJECTIVE:
CENTRAL CONFLICT:
EMOTIONAL STAKES:
TOTAL RUNTIME:
TIMED SCENE BREAKDOWN (start-end time, action, dialogue, turning point, purpose):
ESCALATION:
PAYOFF / FINAL REVERSAL / CLIFFHANGER:
CHARACTER AND LOCATION REQUIREMENTS:
CONTINUITY FACTS:
OPEN QUESTIONS:"""
    raise ValueError(f"{project_type} is not a compact script format.")


def build_compact_generation_instruction(project_type, duration_seconds):
    """Return generation instructions for a complete compact-format screenplay."""
    guidance = build_format_guidance(project_type, duration_seconds)
    if project_type in {"Advertisement", "TVC"}:
        output = (
            "Write the COMPLETE commercial, covering every timed segment in the approved blueprint. "
            "Use clear shot/scene labels and time ranges, filmable visual action, dialogue/VO, "
            "sound/music and supers/end-card text as appropriate. Make the brand/message clear "
            "without adding unsupported claims. Output the commercial script only."
        )
    else:
        output = (
            "Write the COMPLETE micro-drama, covering the full arc and every timed scene in the "
            "approved blueprint. Use screenplay scene headings, filmable action, playable "
            "dialogue and the specified payoff/reversal. Maintain the selected runtime through "
            "the timed scene progression. Output the screenplay only."
        )
    return guidance + "\n\n" + output
