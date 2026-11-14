"""SQLite-backed Story Bible storage for Screenwriter Studio.

All persistence is local to the user's machine. This module uses only Python's
standard library and is deliberately independent of Streamlit and Ollama.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("SCREENWRITER_DB_PATH") or Path(__file__).with_name("screenwriter_studio.db"))

CATEGORIES = ("character", "location", "prop", "timeline")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect(db_path=None):
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def init_db(db_path=None):
    """Create the project and Story Bible tables if they do not exist."""
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL COLLATE NOCASE UNIQUE,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS story_bible_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                category TEXT NOT NULL CHECK(category IN ('character', 'location', 'prop', 'timeline')),
                name TEXT NOT NULL COLLATE NOCASE,
                data_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, category, name),
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_story_bible_project_category
            ON story_bible_entries(project_id, category);

            CREATE TABLE IF NOT EXISTS project_workspaces (
                project_id INTEGER PRIMARY KEY,
                screenplay TEXT NOT NULL DEFAULT '',
                scene_plan TEXT NOT NULL DEFAULT '',
                scene_plan_approved INTEGER NOT NULL DEFAULT 0,
                script_before_doctor TEXT NOT NULL DEFAULT '',
                last_assistant TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )


def upsert_project(title, metadata=None, db_path=None):
    """Create a project or update its metadata, returning its stable integer ID."""
    title = (title or "").strip()
    if not title:
        raise ValueError("Project title cannot be empty.")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError("Project metadata must be a dictionary.")

    now = _now()
    encoded = json.dumps(metadata, ensure_ascii=False)
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO projects(title, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (title, encoded, now, now),
        )
        row = connection.execute(
            "SELECT id FROM projects WHERE title = ? COLLATE NOCASE", (title,)
        ).fetchone()
        return int(row["id"])


def get_project_id(title, db_path=None):
    title = (title or "").strip()
    if not title:
        return None
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM projects WHERE title = ? COLLATE NOCASE", (title,)
        ).fetchone()
        return int(row["id"]) if row else None


def get_project_metadata(project_id, db_path=None):
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT metadata_json FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    return json.loads(row["metadata_json"]) if row else {}



def list_projects(db_path=None):
    """Return saved projects with their basic metadata, newest updated first."""
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT id, title, metadata_json, created_at, updated_at FROM projects ORDER BY updated_at DESC, title COLLATE NOCASE"
        ).fetchall()
    projects = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json"))
        projects.append(item)
    return projects


def load_project_workspace(project_id, db_path=None):
    """Load a saved writing workspace, returning safe defaults for new projects."""
    with _connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT screenplay, scene_plan, scene_plan_approved,
                   script_before_doctor, last_assistant, updated_at
            FROM project_workspaces WHERE project_id = ?
            """,
            (project_id,),
        ).fetchone()
    if row is None:
        return {
            "screenplay": "",
            "scene_plan": "",
            "scene_plan_approved": False,
            "script_before_doctor": "",
            "last_assistant": "",
            "updated_at": None,
        }
    return {
        "screenplay": row["screenplay"],
        "scene_plan": row["scene_plan"],
        "scene_plan_approved": bool(row["scene_plan_approved"]),
        "script_before_doctor": row["script_before_doctor"],
        "last_assistant": row["last_assistant"],
        "updated_at": row["updated_at"],
    }


def save_project_workspace(
    project_id,
    screenplay="",
    scene_plan="",
    scene_plan_approved=False,
    script_before_doctor="",
    last_assistant="",
    db_path=None,
):
    """Save all resumable writing state for one project."""
    if project_id is None:
        raise ValueError("A project must be selected before saving the workspace.")
    values = {
        "screenplay": screenplay,
        "scene_plan": scene_plan,
        "script_before_doctor": script_before_doctor,
        "last_assistant": last_assistant,
    }
    for field, value in values.items():
        if not isinstance(value, str):
            raise ValueError(f"{field} must be text.")
    now = _now()
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO project_workspaces(
                project_id, screenplay, scene_plan, scene_plan_approved,
                script_before_doctor, last_assistant, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                screenplay = excluded.screenplay,
                scene_plan = excluded.scene_plan,
                scene_plan_approved = excluded.scene_plan_approved,
                script_before_doctor = excluded.script_before_doctor,
                last_assistant = excluded.last_assistant,
                updated_at = excluded.updated_at
            """,
            (
                project_id,
                screenplay,
                scene_plan,
                int(bool(scene_plan_approved)),
                script_before_doctor,
                last_assistant,
                now,
            ),
        )
    return now

def upsert_entry(project_id, category, name, data=None, entry_id=None, db_path=None):
    """Insert a Story Bible record or update an existing record."""
    category = (category or "").strip().lower()
    name = (name or "").strip()
    if category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}.")
    if not name:
        raise ValueError("Entry name cannot be empty.")
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Entry data must be a dictionary.")

    now = _now()
    encoded = json.dumps(data, ensure_ascii=False)
    with _connect(db_path) as connection:
        if entry_id is not None:
            cursor = connection.execute(
                """
                UPDATE story_bible_entries
                SET category = ?, name = ?, data_json = ?, updated_at = ?
                WHERE id = ? AND project_id = ?
                """,
                (category, name, encoded, now, entry_id, project_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Story Bible record was not found in this project.")
            return int(entry_id)

        connection.execute(
            """
            INSERT INTO story_bible_entries(
                project_id, category, name, data_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, category, name) DO UPDATE SET
                data_json = excluded.data_json,
                updated_at = excluded.updated_at
            """,
            (project_id, category, name, encoded, now, now),
        )
        row = connection.execute(
            """
            SELECT id FROM story_bible_entries
            WHERE project_id = ? AND category = ? AND name = ? COLLATE NOCASE
            """,
            (project_id, category, name),
        ).fetchone()
        return int(row["id"])


def list_entries(project_id, category=None, db_path=None):
    """Return ordered project records as dictionaries."""
    if category is not None and category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}.")
    with _connect(db_path) as connection:
        if category:
            rows = connection.execute(
                """
                SELECT id, project_id, category, name, data_json, created_at, updated_at
                FROM story_bible_entries
                WHERE project_id = ? AND category = ?
                ORDER BY name COLLATE NOCASE
                """,
                (project_id, category),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, project_id, category, name, data_json, created_at, updated_at
                FROM story_bible_entries
                WHERE project_id = ?
                ORDER BY category, name COLLATE NOCASE
                """,
                (project_id,),
            ).fetchall()

    result = []
    for row in rows:
        item = dict(row)
        item["data"] = json.loads(item.pop("data_json"))
        result.append(item)
    return result


def delete_entry(entry_id, project_id, db_path=None):
    with _connect(db_path) as connection:
        cursor = connection.execute(
            "DELETE FROM story_bible_entries WHERE id = ? AND project_id = ?",
            (entry_id, project_id),
        )
        return cursor.rowcount > 0


def format_story_bible_context(project_id, db_path=None, max_chars=7000):
    """Format established facts for inclusion in scene-generation prompts."""
    if project_id is None:
        return ""
    entries = list_entries(project_id, db_path=db_path)
    if not entries:
        return ""

    headings = {
        "character": "CHARACTERS",
        "location": "LOCATIONS",
        "prop": "IMPORTANT PROPS",
        "timeline": "TIMELINE / STORY EVENTS",
    }
    sections = ["STORY BIBLE — ESTABLISHED FACTS (preserve these; do not contradict them):"]
    for category in CATEGORIES:
        group = [entry for entry in entries if entry["category"] == category]
        if not group:
            continue
        sections.append(f"\n{headings[category]}:")
        for entry in group:
            details = "; ".join(
                f"{key.replace('_', ' ').title()}: {value}"
                for key, value in entry["data"].items()
                if value is not None and str(value).strip()
            )
            sections.append(f"- {entry['name']}" + (f" — {details}" if details else ""))
    formatted = "\n".join(sections)
    if len(formatted) > max_chars:
        formatted = formatted[:max_chars].rsplit("\n", 1)[0] + "\n[Additional Story Bible facts omitted from this prompt.]"
    return formatted
