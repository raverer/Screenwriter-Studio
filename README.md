# Screenwriter Studio

![Python tests](https://github.com/raverer/Screenwriter-Studio/actions/workflows/ci.yml/badge.svg?branch=fix/groq-model-selection)

A local-first, AI-assisted screenwriting workspace built with Python, Streamlit, SQLite, and Ollama.

Screenwriter Studio helps a writer plan scenes, generate screenplay drafts, preserve project facts, check selected continuity rules, and resume work across sessions.

## Features

- **Local LLM writing:** generate screenplay scenes using a locally running Ollama model.
- **Human-approved Scene Blueprint:** plan a scene, review and edit its objectives, conflict, beats, turning point, and continuity notes, then approve it before generation.
- **Project library and resume:** switch between saved projects. Project settings, screenplay drafts, scene blueprints, approval state, Script Doctor comparison drafts, and studio notes autosave locally to SQLite.
- **Persistent Story Bible:** maintain project-specific records for characters, locations, props, and timeline events.
- **Writer-reviewed Story Bible extraction:** ask the local model to propose structured records from a screenplay, edit the JSON, and explicitly approve saving. Existing matching records require a separate overwrite confirmation.
- **Continuity context:** saved Story Bible facts are automatically included in scene-planning and screenplay-generation prompts.
- **Continuity checking:** deterministic checks compare explicit character-age references in screenplay text with numeric ages stored in the Story Bible.
- **Screenplay validation:** deterministic heuristic checks for common formatting issues such as missing scene headings, likely INT./EXT. mismatches, repeated transitions, and camera directions.
- **Script Doctor:** request a full screenplay revision while retaining the previous version for comparison.
- **Export:** download screenplay drafts as DOCX or PDF.\n- **Story structure knowledge library:** explore seven narrative frameworks with their core engines, genre affinities, audience experiences, strengths, cautions, and structural components.\n- **Explainable structure recommendations:** rank frameworks using genre, intended audience experience, and dominant storytelling engine; show match reasons, score breakdowns, cautions, and complementary structures.

## Architecture

- `app.py` — Streamlit application, project setup, project switching, generation workflow, and exports.
- `story_bible.py` — SQLite persistence layer for project metadata, resumable writing workspaces, and Story Bible records. Independent of Streamlit and Ollama.
- `story_bible_ui.py` — Streamlit create, read, update, and delete interface for Story Bible records.
- `story_bible_extractor.py` — extraction prompt, JSON/schema validation, and explicit-approval persistence.
- `story_bible_extraction_ui.py` — extract, review, edit, resolve conflicts, and approve saving.
- `continuity_checker.py` — deterministic character-age continuity checks against Story Bible entries.
- `screenplay_validator.py` — deterministic, dependency-free screenplay formatting checks.\n- `story_structure.py` — structured reference definitions for seven narrative frameworks.\n- `structure_recommender.py` — explainable, deterministic recommendations based on genre, audience experience, and storytelling engine.
- `tests/` — unit tests for persistence, extraction, continuity checks, validation, and the deferred experimental evaluator.

For the component diagram, data flows, persistence model, and implementation boundaries, see [the architecture document](docs/ARCHITECTURE.md). For the seven frameworks and recommendation scoring method, see [the Story Structure Engine guide](docs/STORY_STRUCTURE_ENGINE.md).

The story-structure recommender is deterministic and explainable; it is a creative heuristic, not a scientifically validated genre classifier or probability model. No single structure is required for a genre.\n\nThe Story Bible can be maintained manually or populated from writer-reviewed extraction candidates. Model output is not saved until the writer reviews and approves it. Continuity checking currently covers explicit numeric character-age references only; other contradictions require human review. Semantic retrieval / RAG is not implemented yet.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running
- A model available locally in Ollama (the default configured model is `llama3:latest`)

## Run locally

Clone the repository and enter the project directory:

```bash
git clone https://github.com/raverer/Screenwriter-Studio.git
cd Screenwriter-Studio
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Pull the default model if it is not already installed:

```bash
ollama pull llama3:latest
```

Start Ollama, then launch the app:

```bash
streamlit run app.py
```

To use a different Ollama host, set `OLLAMA_HOST` before launching the app. The default is `http://localhost:11434`.

## Project workspaces and Story Bible storage

Saved projects appear in the **Saved projects** selector in the sidebar. Choose a project and click **Load selected project** to restore its settings, screenplay, Scene Blueprint, approval status, Script Doctor comparison draft, studio notes, and Story Bible. Use **New project / Clear workspace** before starting another project. The active project title is locked to prevent accidentally moving work into a different project. Workspace changes autosave locally as you use the app.

Existing projects created before workspace persistence was added keep their project settings and Story Bible records. They have no previously saved screenplay workspace to restore; paste or recreate an old draft once and it will autosave from then on.

The SQLite database is stored locally in `screenwriter_studio.db` next to the application. It is created automatically and excluded from Git by `.gitignore`. It stores project metadata, writing workspaces, and Story Bible entries.

To store the database elsewhere, set `SCREENWRITER_DB_PATH` to a database file path before launching the app.

Projects are separated by project title. Within a project, Story Bible entries are organised into four categories:

- **Characters:** age, role, personality, motivation, relationships, continuity facts.
- **Locations:** type, description, time/atmosphere, visual details.
- **Props:** description, owner, story significance, continuity facts.
- **Timeline:** when an event occurs, what happens, people involved, consequences.

Keep a backup of the local database if you need to preserve project data across machines. The app does not sync project data to GitHub.

## Run tests

From the project root, with the virtual environment activated:

```bash
python -m unittest discover -s tests -v
```

## Continuous Integration

GitHub Actions runs the unit test suite on pushes and pull requests using Python 3.10 and 3.11. The workflow is defined in `.github/workflows/ci.yml`.

Run the same test command locally before pushing:

```bash
python -m unittest discover -s tests -v
```

## Current limitations

- Story Bible extraction processes only the first 8,000 screenplay characters in this version.
- Continuity information is added to prompts as bounded text context. A retrieval-augmented generation (RAG) pipeline is not implemented yet.
- Screenplay formatting and continuity checks use narrow deterministic rules; review all findings and missed cases manually.
- Local model output quality and response speed depend on the selected model and available hardware.
- The scene evaluator is experimental and is not part of the active Streamlit workflow.

## Privacy

Inference is sent to the configured Ollama server. With the default local Ollama setup, prompts are processed on the local machine. The SQLite project database is also stored locally. Do not expose local database files, secrets, or private screenplay material in public repositories.
