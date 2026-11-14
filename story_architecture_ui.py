"""Streamlit interface for story architecture recommendations and review."""
import json

import streamlit as st

from story_structure import get_structure, list_structures
from structure_recommender import ENGINE_LABELS, recommend_structures
from story_architecture import (
    generate_architecture,
    parse_architecture_response,
)


def _clear_architecture_state(project_id):
    st.session_state["story_architecture_project_id"] = project_id
    st.session_state["story_architecture_recommendations"] = []
    st.session_state["story_architecture_editor"] = ""
    st.session_state["story_architecture_draft_structure_id"] = None
    st.session_state["story_architecture_approved"] = False
    st.session_state["story_architecture"] = None
    st.session_state["story_architecture_experiences"] = []
    st.session_state["story_architecture_engine"] = ""
    st.session_state["story_architecture_primary_structure"] = "three_act"


def render_story_architecture(project_id, project_details, llm_call):
    """Render recommendation, generation, editing and approval UI.

    Approved architecture remains in Streamlit session state during this phase.
    Project/database persistence is intentionally handled in a later phase.
    """
    if st.session_state.get("story_architecture_project_id") != project_id:
        _clear_architecture_state(project_id)

    st.subheader("🏗️ Story Architecture")
    st.caption(
        "Choose a narrative framework for the whole story, generate a structural "
        "blueprint, then review and approve it before planning individual scenes."
    )

    if project_id is None:
        st.info("Create or load a project before generating its story architecture.")
        return None

    structures = list_structures()
    experience_options = sorted({
        item
        for structure in structures
        for item in structure["audience_experiences"]
    })
    engine_ids = list(ENGINE_LABELS.keys())

    with st.expander("Find a suitable story structure", expanded=True):
        selected_experiences = st.multiselect(
            "What should the audience experience?",
            experience_options,
            key="story_architecture_experiences",
            format_func=lambda value: value.replace("_", " ").title(),
            help="Choose one or more intended audience responses. You can leave this blank.",
        )
        selected_engine = st.selectbox(
            "What drives the story?",
            [""] + engine_ids,
            key="story_architecture_engine",
            format_func=lambda value: (
                "Choose a storytelling engine" if not value
                else ENGINE_LABELS[value]
            ),
        )

        try:
            recommendation = recommend_structures(
                genre=project_details.get("genre") or None,
                audience_experience=selected_experiences or None,
                storytelling_engine=selected_engine or None,
                limit=3,
            )
            st.session_state["story_architecture_recommendations"] = (
                recommendation["recommendations"]
            )
            if recommendation["fallback_used"]:
                st.info(
                    "No direct match was found for the selected criteria. "
                    "Three-Act Structure is shown as a flexible starting point."
                )
            for index, item in enumerate(recommendation["recommendations"], start=1):
                with st.container(border=True):
                    st.markdown(
                        f"**{index}. {item['name']}** · "
                        f"{item['score']}/{item['max_score']} heuristic points"
                    )
                    for reason in item["match_reasons"]:
                        st.write(f"- {reason}")
                    st.caption("Considerations: " + " ".join(item["cautions"]))
            st.caption(recommendation["method"]["note"])
        except ValueError as exc:
            st.warning(str(exc))
            recommendation = {"recommendations": [], "fallback_used": False}

    recommendation_items = st.session_state.get(
        "story_architecture_recommendations", []
    )
    recommended_ids = [item["structure_id"] for item in recommendation_items]
    all_ids = [item["id"] for item in structures]
    default_id = recommended_ids[0] if recommended_ids else "three_act"
    default_index = all_ids.index(default_id)

    selected_structure_id = st.selectbox(
        "Primary story structure",
        all_ids,
        index=default_index,
        key="story_architecture_primary_structure",
        format_func=lambda value: get_structure(value)["name"],
        help="You can override the recommendation and select any of the seven frameworks.",
    )

    selected_structure = get_structure(selected_structure_id)
    st.write(f"**Core principle:** {selected_structure['core_principle']}")
    st.caption(
        "Components: " + " → ".join(selected_structure["components"])
    )

    if st.button(
        "✨ Generate Story Architecture",
        use_container_width=True,
        key="generate_story_architecture_button",
    ):
        try:
            with st.spinner(
                f"Building a {selected_structure['name']} story architecture…"
            ):
                architecture = generate_architecture(
                    selected_structure_id, project_details, llm_call
                )
            st.session_state["story_architecture_editor"] = json.dumps(
                architecture, ensure_ascii=False, indent=2
            )
            st.session_state["story_architecture_draft_structure_id"] = (
                selected_structure_id
            )
            st.session_state["story_architecture_approved"] = False
            st.session_state["story_architecture"] = None
            st.success(
                "Story architecture generated. Review and edit the blueprint below."
            )
        except Exception as exc:
            st.error(f"Story architecture generation failed: {exc}")

    draft_text = st.session_state.get("story_architecture_editor", "")
    if draft_text:
        draft_structure_id = st.session_state.get(
            "story_architecture_draft_structure_id"
        )
        if draft_structure_id != selected_structure_id:
            st.warning(
                "The selected structure has changed since this blueprint was generated. "
                "Generate a new blueprint before approving it."
            )
        else:
            st.markdown("#### Review and edit architecture")
            st.text_area(
                "Story architecture JSON",
                key="story_architecture_editor",
                height=520,
                help=(
                    "Edit story events, character arc, conflict, stakes and beat details. "
                    "The structure ID and exact ordered component list must remain valid."
                ),
            )
            if st.button(
                "✓ Validate and approve Story Architecture",
                use_container_width=True,
                key="approve_story_architecture_button",
            ):
                try:
                    validated = parse_architecture_response(
                        st.session_state["story_architecture_editor"],
                        selected_structure_id,
                    )
                    st.session_state["story_architecture"] = validated
                    st.session_state["story_architecture_approved"] = True
                    st.success(
                        "Story Architecture approved for this project session."
                    )
                except Exception as exc:
                    st.session_state["story_architecture_approved"] = False
                    st.session_state["story_architecture"] = None
                    st.error(f"Architecture validation failed: {exc}")

    approved = st.session_state.get("story_architecture_approved", False)
    if approved:
        st.success(
            f"Approved: {get_structure(selected_structure_id)['name']}. "
            "This approval currently lasts for this app session only."
        )
        st.caption(
            "Project persistence and using this architecture to guide Scene Blueprint "
            "generation are planned integration steps."
        )
        return st.session_state.get("story_architecture")

    return None
