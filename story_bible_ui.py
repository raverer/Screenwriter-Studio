"""Streamlit UI for creating and maintaining a project's Story Bible."""
import sqlite3

import streamlit as st

from story_bible import (
    delete_entry,
    list_entries,
    upsert_entry,
)

STORY_BIBLE_FIELDS = {
    "character": [
        ("age", "Age", False),
        ("occupation_or_role", "Occupation / role", False),
        ("personality", "Personality", True),
        ("goal_motivation", "Goal / motivation", True),
        ("relationships", "Relationships", True),
        ("continuity_notes", "Continuity facts to preserve", True),
    ],
    "location": [
        ("place_type", "Interior / exterior / type", False),
        ("description", "Description", True),
        ("atmosphere_time", "Typical time / atmosphere", False),
        ("key_details", "Key visual details", True),
    ],
    "prop": [
        ("description", "Description", True),
        ("owner_custodian", "Owner / custodian", False),
        ("story_significance", "Story significance", True),
        ("continuity_notes", "Continuity facts to preserve", True),
    ],
    "timeline": [
        ("when", "When does it happen?", False),
        ("event", "What happens?", True),
        ("characters_involved", "Characters involved", False),
        ("consequences", "Consequences / what changes", True),
    ],
}


def render_story_bible(project_id):
    """Render project-scoped create, read, update and delete controls."""
    with st.container():
        st.subheader("📚 Story Bible — project memory")
        if project_id is None:
            st.info("Enter a project title in the sidebar to create and save its Story Bible.")
            return

        st.caption(
            "Records are saved locally in SQLite and automatically included in future "
            "scene-planning and screenplay-generation prompts."
        )
        category_labels = {
            "Character": "character",
            "Location": "location",
            "Prop": "prop",
            "Timeline event": "timeline",
        }
        selected_label = st.selectbox(
            "Record type", list(category_labels), key="story_bible_new_category"
        )
        category = category_labels[selected_label]

        with st.form("story_bible_add_form", clear_on_submit=True):
            entry_name = st.text_input("Name / event title")
            new_data = {}
            for field, label, multiline in STORY_BIBLE_FIELDS[category]:
                widget_key = f"story_bible_add_{category}_{field}"
                if multiline:
                    new_data[field] = st.text_area(label, key=widget_key)
                else:
                    new_data[field] = st.text_input(label, key=widget_key)
            add_submitted = st.form_submit_button("Add to Story Bible")

        if add_submitted:
            try:
                upsert_entry(
                    project_id,
                    category,
                    entry_name,
                    {key: value.strip() for key, value in new_data.items() if value.strip()},
                )
                st.success(f"Saved {selected_label.lower()}: {entry_name.strip()}")
            except (ValueError, sqlite3.IntegrityError) as exc:
                if isinstance(exc, sqlite3.IntegrityError):
                    st.error(
                        "An entry with this name already exists in this category. "
                        "Edit the existing record instead."
                    )
                else:
                    st.error(str(exc))

        entries = list_entries(project_id)
        st.markdown("#### Saved story facts")
        if not entries:
            st.info(
                "No Story Bible records yet. Add your first character, location, prop "
                "or timeline event above."
            )
            return

        tabs = st.tabs(["Characters", "Locations", "Props", "Timeline"])
        tab_categories = ["character", "location", "prop", "timeline"]
        for tab, tab_category in zip(tabs, tab_categories):
            with tab:
                category_entries = [
                    entry for entry in entries if entry["category"] == tab_category
                ]
                if not category_entries:
                    st.caption("No records in this section yet.")
                for entry in category_entries:
                    with st.expander(entry["name"], expanded=False):
                        with st.form(f"story_bible_edit_{entry['id']}"):
                            edited_name = st.text_input(
                                "Name / event title",
                                value=entry["name"],
                                key=f"story_bible_name_{entry['id']}",
                            )
                            edited_data = {}
                            for field, label, multiline in STORY_BIBLE_FIELDS[tab_category]:
                                value = str(entry["data"].get(field, ""))
                                widget_key = f"story_bible_{field}_{entry['id']}"
                                if multiline:
                                    edited_data[field] = st.text_area(
                                        label, value=value, key=widget_key
                                    )
                                else:
                                    edited_data[field] = st.text_input(
                                        label, value=value, key=widget_key
                                    )
                            save_submitted = st.form_submit_button("Save changes")

                        if save_submitted:
                            try:
                                upsert_entry(
                                    project_id,
                                    tab_category,
                                    edited_name,
                                    {
                                        key: value.strip()
                                        for key, value in edited_data.items()
                                        if value.strip()
                                    },
                                    entry_id=entry["id"],
                                )
                                st.success("Story Bible record updated.")
                            except (ValueError, sqlite3.IntegrityError) as exc:
                                if isinstance(exc, sqlite3.IntegrityError):
                                    st.error(
                                        "Another record in this category already uses that name."
                                    )
                                else:
                                    st.error(str(exc))

                        confirm_delete = st.checkbox(
                            "Confirm deletion",
                            key=f"story_bible_confirm_delete_{entry['id']}",
                        )
                        if st.button(
                            "Delete record",
                            key=f"story_bible_delete_{entry['id']}",
                            disabled=not confirm_delete,
                        ):
                            delete_entry(entry["id"], project_id)
                            st.success(f"Deleted: {entry['name']}")
                            st.rerun()
