"""Streamlit review-and-approve workflow for automatic Story Bible extraction."""
import json

import streamlit as st

from story_bible import list_entries
from story_bible_extractor import (
    build_extraction_prompt,
    parse_extraction_response,
    save_extracted_entries,
)


def render_story_bible_extraction(project_id, screenplay, model, llm_call):
    """Extract draft records, let the writer edit them, and save only on approval."""
    st.subheader("✨ Extract Story Bible from screenplay")
    st.caption(
        "The local model proposes facts from the current screenplay. Review and edit "
        "the JSON before saving; extraction alone never changes your Story Bible."
    )

    st.session_state.setdefault("story_bible_extraction_editor", "")
    st.session_state.setdefault("story_bible_extraction_saved_snapshot", "")

    if st.button(
        "Extract Story Bible",
        use_container_width=True,
        disabled=project_id is None or not screenplay.strip(),
        key="extract_story_bible_button",
    ):
        try:
            with st.spinner(f"Extracting Story Bible candidates with {model}…"):
                raw = llm_call(
                    "You extract conservative, screenplay-grounded facts. Return only the requested JSON. Never invent missing details.",
                    build_extraction_prompt(screenplay),
                )
                records = parse_extraction_response(raw)
            st.session_state.story_bible_extraction_editor = json.dumps(
                {"entries": records}, ensure_ascii=False, indent=2
            )
            st.session_state.story_bible_extraction_saved_snapshot = ""
            st.session_state.story_bible_extraction_overwrite = False
            st.success(f"Extracted {len(records)} candidate record(s). Review them below.")
        except Exception as exc:
            st.error(f"Story Bible extraction failed: {exc}")

    if project_id is None:
        st.info("Enter a project title in the sidebar before extracting Story Bible records.")
        return
    if not screenplay.strip():
        st.info("Generate or paste a screenplay before extracting Story Bible records.")
        return

    candidate_text = st.text_area(
        "Review and edit extracted records (JSON)",
        key="story_bible_extraction_editor",
        height=320,
        help="You can correct names or details and remove unsupported candidates. Save is enabled only when the JSON is valid.",
    )
    if not candidate_text.strip():
        return

    try:
        candidates = parse_extraction_response(candidate_text)
    except ValueError as exc:
        st.error(f"Cannot approve these records yet: {exc}")
        return

    if not candidates:
        st.info("No reliable Story Bible facts were found. No records have been saved.")
        return

    existing = list_entries(project_id)
    existing_by_key = {
        (entry["category"], entry["name"].strip().casefold()): entry
        for entry in existing
    }
    conflicts = [
        candidate for candidate in candidates
        if (candidate["category"], candidate["name"].strip().casefold()) in existing_by_key
    ]
    created_count = len(candidates) - len(conflicts)
    st.caption(
        f"{len(candidates)} candidate(s): {created_count} new, {len(conflicts)} matching existing record(s)."
    )

    allow_overwrite = False
    if conflicts:
        names = ", ".join(item["name"] for item in conflicts)
        st.warning(
            "These records already exist: "
            + names
            + ". They will not be changed unless you explicitly approve updating them."
        )
        allow_overwrite = st.checkbox(
            "I reviewed these candidates and approve updating matching Story Bible records.",
            key="story_bible_extraction_overwrite",
        )

    already_saved = (
        st.session_state.story_bible_extraction_saved_snapshot == candidate_text
    )
    if already_saved:
        st.success("These reviewed candidates have already been saved.")
    else:
        if st.button(
            "Approve and save to Story Bible",
            type="primary",
            use_container_width=True,
            disabled=not candidates or (bool(conflicts) and not allow_overwrite),
            key="approve_story_bible_extraction",
        ):
            try:
                summary = save_extracted_entries(
                    project_id,
                    candidates,
                    allow_overwrite=allow_overwrite,
                )
                st.session_state.story_bible_extraction_saved_snapshot = candidate_text
                st.success(
                    f"Saved {summary['created']} new record(s) and updated "
                    f"{summary['updated']} existing record(s)."
                )
            except (ValueError, TypeError) as exc:
                st.error(f"Could not save extracted records: {exc}")
