"""Deterministic Story Bible continuity checks (initial rule set: character ages)."""
import re


def _expected_age(value):
    match = re.search(r"\b(\d{1,3})\b", str(value or ""))
    return int(match.group(1)) if match else None


def _age_patterns(character_name):
    name = re.escape(character_name)
    return [
        re.compile(rf"\b{name}\b\s*,\s*(\d{{1,3}})\b", re.IGNORECASE),
        re.compile(rf"\b{name}\b\s*\(\s*(\d{{1,3}})\s*\)", re.IGNORECASE),
        re.compile(rf"\b{name}\b\s+is\s+(\d{{1,3}})(?:\s+years?\s+old)?\b", re.IGNORECASE),
        re.compile(rf"\b{name}\b\s+(\d{{1,3}})\s+years?\s+old\b", re.IGNORECASE),
        re.compile(rf"\b(\d{{1,3}})[- ]year[- ]old\s+{name}\b", re.IGNORECASE),
    ]


def check_continuity(screenplay, story_bible_entries):
    """Find explicit numeric character-age conflicts against saved Story Bible facts.

    This first rule set intentionally checks only age references expressed in
    common screenplay prose formats. It does not infer ages or assess other
    kinds of continuity.
    """
    if not isinstance(screenplay, str):
        raise TypeError("Screenplay must be text.")
    if not isinstance(story_bible_entries, list):
        raise TypeError("Story Bible entries must be a list.")

    findings = []
    checked_characters = 0
    if not screenplay.strip():
        return {"findings": findings, "checked_characters": checked_characters}

    lines = screenplay.splitlines()
    for entry in story_bible_entries:
        if entry.get("category") != "character":
            continue
        name = str(entry.get("name", "")).strip()
        data = entry.get("data") or {}
        expected = _expected_age(data.get("age"))
        if not name or expected is None:
            continue

        checked_characters += 1
        seen = set()
        patterns = _age_patterns(name)
        for line_number, line in enumerate(lines, start=1):
            for pattern in patterns:
                for match in pattern.finditer(line):
                    found = int(match.group(1))
                    if found == expected or (found, line_number) in seen:
                        continue
                    seen.add((found, line_number))
                    findings.append({
                        "type": "character_age",
                        "character": name,
                        "expected_age": expected,
                        "found_age": found,
                        "line": line_number,
                        "excerpt": line.strip(),
                        "message": (
                            f"{name} is listed as {expected} in the Story Bible, "
                            f"but line {line_number} describes them as {found}."
                        ),
                    })

    return {
        "findings": findings,
        "checked_characters": checked_characters,
    }
