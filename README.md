# Screenwriter Studio

![Python tests](https://github.com/raverer/Screenwriter-Studio/actions/workflows/ci.yml/badge.svg?branch=main)

A local-first, AI-assisted screenwriting workspace built with Python, Streamlit, SQLite, and Ollama.

Screenwriter Studio helps writers develop feature films, series, short films, advertisements, TVCs and micro dramas; preserve project facts and research; and resume work across sessions.

## Features

- **Local LLM writing:** generate screenplay scenes using a locally running Ollama model.
- **Human-approved Scene Blueprint:** for feature films, series and short films, plan a scene, review and edit its objectives, conflict, beats, turning point and continuity notes, then approve it before generation.
- **Commercial and Micro Drama formats:** choose Advertisement or TVC (15–120 seconds), or Micro Drama (150–200 seconds). Set the target runtime in seconds; it is saved with the project and included in prompts.
- **Complete short-form workflow:** Advertisement, TVC and Micro Drama use a full-script blueprint with timed shots/scenes. The writer reviews and approves the entire timed blueprint before generating the complete script, rather than generating one scene at a time.
- **Commercial writing guidance:** advertisement/TVC prompts focus on a fast audience hook, one clear brand proposition, benefit, brand moment and CTA where appropriate. The model is instructed not to invent product claims, prices, offers, endorsements or legal copy.
- **Micro Drama writing guidance:** prompts target a complete dramatic arc with an immediate hook, central conflict, escalation and payoff/reversal/cliffhanger.
- **Project library and resume:** switch between saved projects. Project settings, screenplay drafts, scene blueprints, approval state, Script Doctor comparison drafts, and studio notes autosave locally to SQLite.
- **Persistent Story Bible:** maintain project-specific records for characters, locations, props, and timeline events.
- **Writer-reviewed Story Bible extraction:** ask the local model to propose structured records from a screenplay, edit the JSON, and explicitly approve saving. Existing matching records require a separate overwrite confirmation.
- **Continuity context:** saved Story Bible facts are automatically included in scene-planning and screenplay-generation prompts.
- **Continuity checking:** deterministic checks compare explicit character-age references in screenplay text with numeric ages stored in the Story Bible.
- **Screenplay validation:** deterministic heuristic checks for common formatting issues such as missing scene headings, likely INT./EXT. mismatches, repeated transitions, and camera directions.
- **Script Doctor:** request a full screenplay revision while retaining the previous version for comparison.
- **Research Library with RAG:** upload PDF, DOCX, TXT and Markdown sources per project; extract text, split it into overlapping chunks, create local Ollama embeddings, and store vectors in SQLite. Search semantically with cosine similarity and inspect matching excerpts with source filename, PDF page and similarity score.
- **Research-grounded writing (opt-in):** enable retrieved research in AI prompts to add the top relevant, source-labelled excerpts to scene planning and screenplay writing. Research sources are kept separate from Story Bible facts and story canon.
- **Export:** download screenplay drafts as DOCX or PDF.
- **Story structure knowledge library (Python module):** structured definitions for seven narrative frameworks, including their core engines, genre affinities, audience experiences, strengths, cautions, and structural components.
- **Explainable structure recommendations:** rank frameworks using project genre, intended audience experience, and dominant storytelling engine; show match reasons, heuristic score breakdowns, cautions, and complementary structures.
- **Persistent Story Architecture Blueprint:** generate a structure-specific story-wide outline, edit its JSON, and explicitly approve it after validation of required fields and the exact ordered beat sequence. Approved architecture is saved per project in SQLite, restored when the project is loaded, and included in scene-planning and screenplay-generation context.

## Supported screenplay formats

| Format | Target runtime | Writing workflow |
|---|---:|---|
| Feature Film | No fixed limit | Scene-by-scene planning and generation |
| OTT / Web Series | No fixed limit | Scene-by-scene planning and generation |
| Short Film | No fixed limit | Scene-by-scene planning and generation |
| Advertisement | 15–120 seconds | Complete timed commercial blueprint, then complete script |
| TVC | 15–120 seconds | Complete timed television-commercial blueprint, then complete script |
| Micro Drama | 150–200 seconds | Complete timed dramatic blueprint, then complete script |

Advertisement, TVC and Micro Drama runtimes are inclusive of the stated endpoints and selected in whole seconds. The target duration is stored in project metadata. Changing the format or target runtime invalidates an existing scene blueprint and approved Story Architecture, because those plans were generated against different constraints.

For commercials, the writing prompt accounts for visual action, dialogue/voice-over, sound/music, supers, transitions and end cards. For Micro Drama, it emphasises a complete short dramatic arc rather than an episode outline. The model is instructed to make timed segment durations add up to the selected runtime; actual edit duration still needs a production timing pass.

## Architecture

- `app.py` — Streamlit application, project setup, project switching, generation workflow, and exports.
- `story_bible.py` — SQLite persistence layer for project metadata, resumable writing workspaces, and Story Bible records. Independent of Streamlit and Ollama.
- `story_bible_ui.py` — Streamlit create, read, update, and delete interface for Story Bible records.
- `story_bible_extractor.py` — extraction prompt, JSON/schema validation, and explicit-approval persistence.
- `story_bible_extraction_ui.py` — extract, review, edit, resolve conflicts, and approve saving.
- `continuity_checker.py` — deterministic character-age continuity checks against Story Bible entries.
- `screenplay_validator.py` — deterministic, dependency-free screenplay formatting checks.
- `story_structure.py` — structured reference definitions for seven narrative frameworks.
- `structure_recommender.py` — explainable, deterministic recommendations based on genre, audience experience, and storytelling engine.
- `story_architecture.py` — framework-specific prompt generation, runtime-aware format guidance, injectable Ollama workflow, strict JSON parsing and beat-order validation.
- `screenplay_formats.py` — supported format definitions, runtime ranges, validation, compact-script blueprint sections and generation instructions.
- `story_architecture_ui.py` — Streamlit recommendation, generation, edit and project-persistent approval interface.
- `research_rag.py` — document text extraction, overlapping chunking, Ollama embeddings, project-scoped SQLite vector storage, cosine similarity retrieval, and source-labelled prompt context.
- `research_rag_ui.py` — upload, index, delete and semantically search research documents.
- `tests/` — unit tests for persistence, extraction, continuity checks, screenplay validation, structure recommendations, architecture generation and the deferred experimental evaluator.

For the component diagram, data flows, persistence model, and implementation boundaries, see [the architecture document](docs/ARCHITECTURE.md). For the seven frameworks and recommendation scoring method, see [the Story Structure Engine guide](docs/STORY_STRUCTURE_ENGINE.md).

The story-structure recommender is deterministic and explainable; it is a creative heuristic, not a scientifically validated genre classifier or probability model. No single structure is required for a genre. Story Architecture approval is stored separately from the draft and only approved JSON is restored and added to prompts.

The Story Bible can be maintained manually or populated from writer-reviewed extraction candidates. Model output is not saved until the writer reviews and approves it. Continuity checking currently covers explicit numeric character-age references only; other contradictions require human review. RAG is implemented as a lightweight, exact cosine-similarity scan over project-specific embeddings stored in SQLite; it does not use a separate vector database, hybrid retrieval, a reranker, or a learned retrieval evaluator.

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
ollama pull nomic-embed-text:latest
```

Start Ollama, then launch the app:

```bash
streamlit run app.py
```

To use a different Ollama host, set `OLLAMA_HOST` before launching the app. The default is `http://localhost:11434`.

## Project workspaces and Story Bible storage

Saved projects appear in the **Saved projects** selector in the sidebar. Choose a project and click **Load selected project** to restore its settings, screenplay, Scene Blueprint, approval status, Script Doctor comparison draft, studio notes, and Story Bible. Use **New project / Clear workspace** before starting another project. The active project title is locked to prevent accidentally moving work into a different project. Workspace changes autosave locally as you use the app.

Existing projects created before workspace persistence was added keep their project settings and Story Bible records. They have no previously saved screenplay workspace to restore; paste or recreate an old draft once and it will autosave from then on.

The SQLite database is stored locally in `screenwriter_studio.db` next to the application. It is created automatically and excluded from Git by `.gitignore`. It stores project metadata, writing workspaces, approved Story Architectures, Story Bible entries, research documents, text chunks and embedding vectors.

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

GitHub Actions compiles the Python modules and runs the unit test suite on pushes and pull requests using Python 3.10 and 3.11. The workflow is defined in `.github/workflows/ci.yml`. The test suite covers persistence, story structure and architecture validation, research ingestion, embedding orchestration, project-isolated retrieval and source formatting.

Run the same checks locally before pushing:

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```

## RAG implementation details and limitations

- Supported uploads: PDF, DOCX, TXT and Markdown; each file is limited to 10 MB and 500 chunks.
- Text is split into 220-word chunks with a 40-word overlap. PDF page numbers are retained when text is extracted.
- Ollama generates embeddings through `/api/embed` using `nomic-embed-text:latest` by default. Install it with `ollama pull nomic-embed-text`.
- Embeddings and source text are stored locally in SQLite. Retrieval scans the selected project's vectors and ranks them with cosine similarity. Only documents indexed with the selected embedding model are searched.
- The Research Library search view displays source excerpts. When the sidebar option **Use retrieved research in AI prompts** is enabled, up to four retrieved chunks are added to writing prompts with source filename/page labels.
- The pipeline extracts text from digital PDFs; it does not OCR scanned/image-only PDFs. Complex PDF layouts, tables, footnotes and DOCX formatting may not be preserved accurately.
- Retrieval uses dense embeddings and exact cosine scoring only. There is no hybrid keyword search, approximate-nearest-neighbour index, reranker, retrieval-quality benchmark, or automated source citation in the final screenplay. Writers should inspect the cited excerpts and verify factual claims.
- Story Bible facts represent established story canon; retrieved research is supporting reference material and should not silently override the writer's brief or Story Bible.

## Other limitations

- Story Bible extraction processes only the first 8,000 screenplay characters in this version.
- Screenplay formatting and continuity checks use narrow deterministic rules; review all findings and missed cases manually.
- Local model output quality and response speed depend on the selected model and available hardware.
- The scene evaluator is experimental and is not part of the active Streamlit workflow.

## Privacy

Inference is sent to the configured Ollama server. With the default local Ollama setup, prompts are processed on the local machine. The SQLite project database is also stored locally. Do not expose local database files, secrets, or private screenplay material in public repositories.
