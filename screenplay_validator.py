"""Deterministic, dependency-free screenplay formatting checks.

These checks flag likely issues for human review; they do not judge story quality.
"""
import re
from collections import Counter

SCENE_HEADING_RE = re.compile(r"^(INT\.|EXT\.|INT\./EXT\.|I/E\.)\s+.+", re.IGNORECASE)
OUTDOOR_TERMS = re.compile(
    r"\b(BEACH|PARK|STREET|ROAD|ROOFTOP|GARDEN|FOREST|FIELD|SHORE|DESERT)\b",
    re.IGNORECASE,
)
INDOOR_TERMS = re.compile(
    r"\b(ROOM|OFFICE|KITCHEN|BEDROOM|RESTAURANT|HALLWAY|LIFT|ELEVATOR)\b",
    re.IGNORECASE,
)
TRANSITIONS = {"CUT TO:", "FADE OUT.", "FADE TO BLACK.", "DISSOLVE TO:", "SMASH CUT TO:"}


def _normalise_heading(line):
    return re.sub(r"^\*{1,2}|\*{1,2}$", "", line.strip()).strip()


def validate_screenplay(script):
    """Return a list of (severity, message) findings."""
    if not script or not script.strip():
        return [("error", "Screenplay is empty. Paste or generate a screenplay first.")]

    findings = []
    lines = script.splitlines()
    headings = []
    transitions = Counter()

    for number, raw_line in enumerate(lines, 1):
        line = _normalise_heading(raw_line)
        if SCENE_HEADING_RE.match(line):
            headings.append((number, line))
            if line.upper().startswith("INT.") and OUTDOOR_TERMS.search(line):
                findings.append((
                    "warning",
                    f"Line {number}: '{line}' contains an outdoor location term; check whether EXT. is appropriate.",
                ))
            if line.upper().startswith("EXT.") and INDOOR_TERMS.search(line):
                findings.append((
                    "warning",
                    f"Line {number}: '{line}' contains an indoor location term; check whether INT. is appropriate.",
                ))

        transition = line.upper()
        if transition in TRANSITIONS:
            transitions[transition] += 1
            if transitions[transition] > 1:
                findings.append((
                    "warning",
                    f"Line {number}: repeated transition '{line}' may be unnecessary.",
                ))

    if not headings:
        findings.append(("error", "No standard scene heading found. Expected INT. or EXT. followed by a location and time."))
    else:
        findings.append(("info", f"{len(headings)} scene heading(s) detected."))

    if re.search(r"\bCAMERA\s+(PANS|ZOOMS|MOVES)|\bTHE CAMERA\b", script, re.IGNORECASE):
        findings.append(("warning", "Camera direction detected. Review whether it is essential to the screenplay."))

    if re.search(r"(?im)^\s*(here is|this is) the (written )?scene\s*:?\s*$", script):
        findings.append(("warning", "Introductory assistant commentary detected outside the screenplay."))

    if re.search(r"(?m)^\s*\*{0,2}\d+\*{0,2}\s*$", script):
        findings.append(("warning", "Standalone numbered beat markers detected. Remove them from the finished screenplay."))

    if not any(level in {"warning", "error"} for level, _ in findings):
        findings.append(("success", "No issues detected by the basic formatting checks."))

    findings.append(("info", "Automated checks are heuristic. Confirm scene context and formatting manually."))
    return findings
