# Screenwriter Studio — local Ollama edition
import html
import os
import re
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

import requests
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Preformatted, Spacer, Paragraph

from continuity_checker import check_continuity
from story_bible import (
    format_story_bible_context,
    init_db,
    list_entries,
    list_projects,
    load_project_workspace,
    save_project_workspace,
    upsert_project,
)
from story_bible_ui import render_story_bible
from story_bible_extraction_ui import render_story_bible_extraction

init_db()

st.set_page_config(page_title="Screenwriter Studio", layout="wide")

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = "llama3:latest"
REQUEST_TIMEOUT = 600

for key, default in {
    "script_text": "",
    "last_assistant": "",
    "script_before_doctor": "",
    "project_bible": "",
    "scene_plan": "",
    "scene_plan_approved": False,
    "validation_report": [],
    "continuity_report": None,
    "project_title": "",
    "project_type": "Feature Film",
    "writing_language": "English",
    "project_genre": "",
    "project_tone": "",
    "project_characters": "",
    "project_setting": "",
    "project_logline": "",
    "project_notes": "",
    "project_writing_style": "",
    "project_audience_guidance": "",
    "saved_project_selector": "— Choose a saved project —",
}.items():
    st.session_state.setdefault(key, default)

def get_ollama_models():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        return [m.get("name") for m in response.json().get("models", []) if m.get("name")]
    except requests.RequestException:
        return []

def build_system_prompt(language, project_type):
    return f"""You are an experienced professional screenwriter and screenplay editor.
Write in {language}. This language choice applies to ALL spoken dialogue, action,
scene headings and other screenplay text unless the user explicitly requests
code-switching or specifies different language rules.

PROJECT FORMAT: {project_type}.
Use industry-standard screenplay conventions:
- Scene headings in INT./EXT. — LOCATION — TIME format.
- Present-tense, concise, filmable action; show rather than explain.
- Character cues in uppercase; dialogue beneath the cue.
- Parentheticals only when genuinely needed.
- Use transitions sparingly and only when editorially meaningful.
- Introduce a character with their name in uppercase on first appearance.
- Keep action paragraphs readable and avoid novelistic interior thoughts.
- Do not add camera directions unless specifically requested.
- Do not add commentary, explanations, markdown fences, or analysis outside the screenplay.
Maintain cause-and-effect, character voice, geography, timeline and established facts.
Never invent details that contradict the project information or earlier scenes.
Return clean, copy-ready screenplay text."""

def call_ollama(system, user, model, temperature, max_tokens, response_format=None):
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "temperature": temperature,
            "num_ctx": 4096,
            "num_predict": max_tokens,
        },
    }
    if response_format:
        payload["format"] = response_format
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat", json=payload, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        answer = response.json().get("message", {}).get("content", "").strip()
        if not answer:
            raise ValueError("Ollama returned an empty response.")
        return answer
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama. Open the Ollama app or run 'ollama serve', "
            "then confirm 'ollama list' shows your model."
        ) from exc
    except requests.Timeout as exc:
        raise RuntimeError(
            "Ollama took too long to respond. Try a shorter request or reduce the output limit."
        ) from exc
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = response.json().get("error", "")
        except Exception:
            pass
        raise RuntimeError(f"Ollama request failed: {detail or exc}") from exc

def create_docx(script, doc_title):
    document = Document()
    section = document.sections[0]
    section.top_margin, section.bottom_margin = Inches(0.8), Inches(0.8)
    section.left_margin, section.right_margin = Inches(1.2), Inches(1.0)
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Courier New", Pt(12)
    if doc_title.strip():
        heading = document.add_heading(doc_title.strip(), level=1)
        for run in heading.runs:
            run.font.name = "Courier New"
    for line in script.splitlines():
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(line if line else " ")
        run.font.name, run.font.size = "Courier New", Pt(12)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()

def create_pdf(script, doc_title):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=0.75*inch, leftMargin=1.0*inch,
        topMargin=0.7*inch, bottomMargin=0.7*inch, title=doc_title or "Screenplay"
    )
    style = ParagraphStyle("Screenplay", fontName="Courier", fontSize=10, leading=12)
    story = []
    if doc_title.strip():
        story.append(Paragraph(xml_escape(doc_title.strip()), ParagraphStyle(
            "DocumentTitle", parent=style, fontSize=14, leading=18
        )))
        story.append(Spacer(1, 0.2*inch))
    story.append(Preformatted(xml_escape(script), style, maxLineLength=88))
    pdf.build(story)
    return buffer.getvalue()

# Sidebar and project controls
st.sidebar.title("🎬 Screenwriter Studio")
st.sidebar.caption("Local writing powered by Ollama")
models = get_ollama_models()
if models:
    default_index = models.index(DEFAULT_MODEL) if DEFAULT_MODEL in models else 0
    model = st.sidebar.selectbox("Ollama model", models, index=default_index)
    st.sidebar.success("Ollama connected")
else:
    model = st.sidebar.text_input("Ollama model", value=DEFAULT_MODEL)
    st.sidebar.warning("Ollama not detected. Start Ollama before generating.")

temperature = st.sidebar.slider("Creativity", 0.1, 1.2, 0.7, 0.1)
max_tokens = st.sidebar.slider("Maximum output tokens", 512, 4096, 2048, step=256)

st.sidebar.markdown("### Saved projects")
saved_projects = list_projects()
saved_project_titles = ["— Choose a saved project —"] + [item["title"] for item in saved_projects]
selected_saved_project = st.sidebar.selectbox(
    "Open an existing project",
    saved_project_titles,
    key="saved_project_selector",
)
load_project_clicked = st.sidebar.button(
    "📂 Load selected project",
    use_container_width=True,
    disabled=selected_saved_project == "— Choose a saved project —",
)
new_project_clicked = st.sidebar.button("＋ New project / Clear workspace", use_container_width=True)

if load_project_clicked:
    selected_project = next(
        (item for item in saved_projects if item["title"] == selected_saved_project),
        None,
    )
    if selected_project:
        metadata = selected_project["metadata"]
        workspace = load_project_workspace(selected_project["id"])
        st.session_state["project_title"] = selected_project["title"]
        st.session_state["project_type"] = metadata.get("format", "Feature Film")
        st.session_state["writing_language"] = metadata.get("language", "English")
        st.session_state["project_genre"] = metadata.get("genre", "")
        st.session_state["project_tone"] = metadata.get("tone", "")
        st.session_state["project_characters"] = metadata.get("characters", "")
        st.session_state["project_setting"] = metadata.get("setting", "")
        st.session_state["project_logline"] = metadata.get("logline", "")
        st.session_state["project_notes"] = metadata.get("notes", "")
        st.session_state["project_writing_style"] = metadata.get("writing_style", "")
        st.session_state["project_audience_guidance"] = metadata.get("audience_guidance", "")
        st.session_state["script_text"] = workspace["screenplay"]
        st.session_state["scene_plan"] = workspace["scene_plan"]
        st.session_state["scene_plan_editor"] = workspace["scene_plan"]
        st.session_state["scene_plan_approved"] = workspace["scene_plan_approved"]
        st.session_state["scene_plan_approval"] = workspace["scene_plan_approved"]
        st.session_state["script_before_doctor"] = workspace["script_before_doctor"]
        st.session_state["last_assistant"] = workspace["last_assistant"]
        st.session_state["continuity_report"] = None
        st.session_state["validation_report"] = []
        st.session_state["story_bible_extraction_editor"] = ""
        st.session_state["story_bible_extraction_saved_snapshot"] = ""
        st.session_state["story_bible_extraction_project_id"] = None
        st.session_state["story_bible_extraction_source_hash"] = ""
        st.session_state["story_bible_extraction_last_seen"] = ""
        st.session_state["project_loaded_notice"] = f"Loaded project: {selected_project['title']}"

if new_project_clicked:
    for key, value in {
        "project_title": "",
        "project_type": "Feature Film",
        "writing_language": "English",
        "project_genre": "",
        "project_tone": "",
        "project_characters": "",
        "project_setting": "",
        "project_logline": "",
        "project_notes": "",
        "project_writing_style": "",
        "project_audience_guidance": "",
        "script_text": "",
        "scene_plan": "",
        "scene_plan_editor": "",
        "scene_plan_approved": False,
        "scene_plan_approval": False,
        "script_before_doctor": "",
        "last_assistant": "",
        "validation_report": [],
        "continuity_report": None,
        "story_bible_extraction_editor": "",
        "story_bible_extraction_saved_snapshot": "",
        "story_bible_extraction_project_id": None,
        "story_bible_extraction_source_hash": "",
        "story_bible_extraction_last_seen": "",
    }.items():
        st.session_state[key] = value
    st.session_state["project_loaded_notice"] = "New workspace ready. Enter a project title to save it."

st.sidebar.markdown("### Project setup")
title = st.sidebar.text_input("Project title", placeholder="e.g. The Last Local Train", key="project_title")
project_type = st.sidebar.selectbox(
    "Screenplay format",
    ["Feature Film", "OTT / Web Series", "Short Film"],
    key="project_type",
    help="Choose the format for this project.",
)
language = st.sidebar.text_input(
    "Writing language",
    key="writing_language",
    help="Choose any language or mix, e.g. Hindi, Nepali, Hinglish, Malayalam, English with Hindi dialogue.",
)
genre = st.sidebar.text_input("Genre", placeholder="Psychological thriller", key="project_genre")
tone = st.sidebar.text_input("Tone", placeholder="Tense, grounded, atmospheric", key="project_tone")
characters = st.sidebar.text_area("Main characters", placeholder="Name, age, personality, motivation…", key="project_characters")
setting = st.sidebar.text_input("Primary setting", placeholder="Mumbai, present day", key="project_setting")
logline = st.sidebar.text_area("Logline / premise", placeholder="What is the story about?", key="project_logline")
notes = st.sidebar.text_area("Story notes / constraints", placeholder="Themes, plot points, restrictions…", key="project_notes")
writing_style = st.sidebar.text_input("Style reference (optional)", placeholder="Describe qualities, not just a name", key="project_writing_style")
trend_style = st.sidebar.text_input("Audience / genre convention (optional)", key="project_audience_guidance")

current_project_id = None
if title.strip():
    current_project_id = upsert_project(
        title,
        {
            "format": project_type,
            "language": language,
            "genre": genre,
            "tone": tone,
            "characters": characters,
            "setting": setting,
            "logline": logline,
            "notes": notes,
            "writing_style": writing_style,
            "audience_guidance": trend_style,
        },
    )
    st.session_state["active_project_id"] = current_project_id

    known_project_ids = {item["id"] for item in saved_projects}
    if current_project_id not in known_project_ids:
        st.rerun()
else:
    st.session_state["active_project_id"] = None

st.sidebar.markdown("---")
generate_btn = st.sidebar.button("✍️ Generate Scene 1", use_container_width=True)
next_scene_btn = st.sidebar.button("＋ Generate Next Scene", use_container_width=True)
doctor_btn = st.sidebar.button("🩺 AI Script Doctor", use_container_width=True)
plan_opening_btn = st.sidebar.button("🧭 Plan Opening Scene", use_container_width=True)
plan_next_btn = st.sidebar.button("🧭 Plan Next Scene", use_container_width=True)
validate_btn = st.sidebar.button("🔎 Validate Screenplay", use_container_width=True)

def project_context():
    context = f"""PROJECT
Title: {title or 'Untitled'}
Format: {project_type}
Language: {language}
Genre: {genre}
Tone: {tone}
Logline: {logline}
Characters: {characters}
Setting: {setting}
Story notes and constraints: {notes}
Style guidance: {writing_style or 'Cinematic, original and restrained'}
Audience / genre guidance: {trend_style or 'Use genre conventions without clichés'}"""
    bible_context = format_story_bible_context(current_project_id)
    if bible_context:
        context += "\n\n" + bible_context
    return context

system_prompt = build_system_prompt(language.strip() or "English", project_type)

def create_scene_plan(previous_script=""):
    context = project_context()
    task = (f"Plan exactly ONE next scene. Advance the story with a new choice, obstacle and consequence. Avoid repeating the previous scene.\nSCREENPLAY SO FAR:\n{previous_script[-9000:]}"
            if previous_script else
            "Plan the opening scene. Establish the protagonist through behaviour, create a dramatic situation and a compelling hook without rushing the main premise.")
    prompt = f"""{context}

{task}

Consider project format, genre and tone. For comedy, identify character-based or
situational humour. For science fiction, use grounded foreshadowing without
revealing the central mystery too early. Give each major character agency.
Separate the whole-project premise from this scene's specific job.

Return these sections:
SCENE PURPOSE:
FOCUS CHARACTER:
CHARACTER WANT IN THIS SCENE:
SCENE OBJECTIVE:
OBSTACLE:
CONFLICT:
CHARACTER DYNAMIC:
COMEDY / GENRE OPPORTUNITY:
SETUP:
BEATS (4-6 causal beats):
ESCALATION:
TURNING POINT:
ENDING / HOOK:
WHAT CHANGES:
CONTINUITY FACTS:
UNRESOLVED QUESTIONS:
Every beat must cause or motivate the next. Do not write screenplay dialogue."""
    with st.spinner("Llama 3 is designing the scene blueprint…"):
        return call_ollama(
            "You are a professional story editor. Design playable, causal dramatic scenes. Avoid generic beats and decorative events.",
            prompt, model, min(0.35, temperature), 1100
        )

from screenplay_validator import validate_screenplay

def generate_scene_1():
    if not st.session_state.scene_plan.strip() or not st.session_state.scene_plan_approved:
        st.warning("Create a Scene Blueprint, review it, and approve it before generating.")
        return
    prompt = f"""{project_context()}

HUMAN-APPROVED SCENE BLUEPRINT:
{st.session_state.scene_plan}

Write ONLY this scene. Follow its objective, conflict, causal beats, escalation
and turning point. Preserve character facts. Use correct INT./EXT. headings,
one scene heading unless location changes, minimal transitions and no unnecessary
camera directions. Output screenplay text only."""
    with st.spinner("Llama 3 is writing from your approved blueprint…"):
        result = call_ollama(system_prompt, prompt, model, temperature, max_tokens)
    st.session_state.script_text = result
    st.session_state.last_assistant = "Scene generated from your approved blueprint."
    st.session_state.scene_plan = ""
    st.session_state.scene_plan_approved = False
    st.session_state["scene_plan_approval"] = False
    st.session_state.project_bible = project_context()

def generate_next_scene():
    if not st.session_state.script_text.strip():
        st.warning("Generate or paste a screenplay before planning the next scene.")
        return
    if not st.session_state.scene_plan.strip() or not st.session_state.scene_plan_approved:
        st.warning("Create a Scene Blueprint, review it, and approve it before generating.")
        return
    prompt = f"""{project_context()}

HUMAN-APPROVED NEXT-SCENE BLUEPRINT:
{st.session_state.scene_plan}

Write ONLY the next scene. Continue without recap. Follow the approved objective,
conflict, beats and turning point. Preserve established character, location, prop
and timeline facts. Use correct INT./EXT. headings, minimal transitions and no
unnecessary camera directions. Output screenplay text only.

SCREENPLAY SO FAR:
{st.session_state.script_text[-14000:]}"""
    with st.spinner("Llama 3 is writing from your approved blueprint…"):
        result = call_ollama(system_prompt, prompt, model, temperature, max_tokens)
    st.session_state.script_text += "\n\n" + result
    st.session_state.last_assistant = "Next scene generated from your approved blueprint."
    st.session_state.scene_plan = ""
    st.session_state.scene_plan_approved = False
    st.session_state["scene_plan_approval"] = False

def run_script_doctor():
    current = st.session_state.script_text.strip()
    if not current:
        st.warning("Generate or paste a screenplay before using Script Doctor.")
        return
    prompt = f"""{project_context()}

Act as a rigorous screenplay editor. Diagnose and silently fix problems in:
dramatic structure, pacing, scene progression, character motivation and voice,
dialogue/subtext, visual storytelling, repetition, plausibility and continuity.
Preserve the premise, intended genre, tone, characters and important story events.
Do not turn it into a different story. Do not invent unsupported backstory.
Return the COMPLETE revised screenplay, not notes or excerpts. Maintain
industry-standard screenplay format and the selected language.

SCREENPLAY:
{current}"""
    with st.spinner("Llama 3 is reviewing and revising the screenplay…"):
        revised = call_ollama(system_prompt, prompt, model, temperature, max_tokens)
    st.session_state.script_before_doctor = current
    st.session_state.script_text = revised
    st.session_state.last_assistant = "Script Doctor completed a full screenplay revision. Original retained for comparison."
    st.success("Revised screenplay is ready. The previous version is retained below.")

if plan_opening_btn:
    try:
        st.session_state.scene_plan = create_scene_plan()
        st.session_state.scene_plan_approved = False
        st.session_state["scene_plan_approval"] = False
        st.session_state["scene_plan_editor"] = st.session_state.scene_plan
        st.session_state.last_assistant = "Scene Blueprint created. Review and approve it before generation."
    except Exception as exc:
        st.error(str(exc))
if plan_next_btn:
    if not st.session_state.script_text.strip():
        st.warning("Generate or paste a screenplay before planning the next scene.")
    else:
        try:
            st.session_state.scene_plan = create_scene_plan(st.session_state.script_text)
            st.session_state.scene_plan_approved = False
            st.session_state["scene_plan_editor"] = st.session_state.scene_plan
            st.session_state.last_assistant = "Next-scene blueprint created. Review and approve it before generation."
        except Exception as exc:
            st.error(str(exc))
if validate_btn:
    st.session_state.validation_report = validate_screenplay(st.session_state.script_text)

if generate_btn:
    try:
        generate_scene_1()
    except Exception as exc:
        st.error(str(exc))
if next_scene_btn:
    try:
        generate_next_scene()
    except Exception as exc:
        st.error(str(exc))
if doctor_btn:
    try:
        run_script_doctor()
    except Exception as exc:
        st.error(str(exc))

st.title("🎬 Screenwriter Studio")
if st.session_state.get("project_loaded_notice"):
    st.success(st.session_state.pop("project_loaded_notice"))
st.caption(f"Local model: {model} · Format: {project_type} · Language: {language}")
st.caption("Project settings, screenplay drafts, scene plans and Script Doctor comparisons autosave locally.")
render_story_bible(current_project_id)
left, right = st.columns([2, 1])
with left:
    st.subheader("📄 Screenplay")
    st.text_area(
        "Edit your screenplay here",
        key="script_text",
        height=650,
        label_visibility="collapsed",
        placeholder="Your screenplay will appear here. You can also paste or edit a draft."
    )

    render_story_bible_extraction(
        current_project_id,
        st.session_state.script_text,
        model,
        lambda system, prompt: call_ollama(
            system, prompt, model, 0.1, 1500, response_format="json"
        ),
    )

    if st.button("🔍 Check Story Bible continuity", use_container_width=True):
        if not st.session_state.script_text.strip():
            st.session_state.continuity_report = None
            st.warning("Generate or paste a screenplay before checking continuity.")
        elif current_project_id is None:
            st.session_state.continuity_report = None
            st.warning("Enter a project title and add Story Bible records first.")
        else:
            st.session_state.continuity_report = check_continuity(
                st.session_state.script_text,
                list_entries(current_project_id),
            )

    if st.session_state.continuity_report is not None:
        report = st.session_state.continuity_report
        findings = report["findings"]
        st.markdown("### Story Bible continuity report")
        st.caption(
            "Initial deterministic rule set: checks explicit numeric character-age "
            "references against saved Story Bible ages. It does not assess other continuity types."
        )
        st.metric("Characters with numeric ages checked", report["checked_characters"])
        if findings:
            st.warning(f"{len(findings)} possible age contradiction(s) found.")
            for finding in findings:
                st.error(finding["message"])
                st.caption(f"Line {finding['line']}: {finding['excerpt']}")
        elif report["checked_characters"]:
            st.success("No explicit character-age contradictions found.")
        else:
            st.info("No character records with numeric ages were available to check.")
with right:
    st.subheader("🧭 Scene Blueprint")
    if st.session_state.scene_plan:
        st.text_area("Review and edit the blueprint", key="scene_plan_editor", height=390)
        st.session_state.scene_plan = st.session_state.scene_plan_editor
        st.session_state.scene_plan_approved = st.checkbox(
            "I have reviewed and approve this blueprint",
            value=st.session_state.scene_plan_approved,
            key="scene_plan_approval"
        )
        if st.session_state.scene_plan_approved:
            st.success("Blueprint approved. You can now generate the scene.")
        else:
            st.caption("Generation is locked until you approve the blueprint.")
    else:
        st.caption("Plan → Review/edit → Approve → Generate.")
    st.subheader("💬 Studio notes")
    if st.session_state.last_assistant:
        st.info(st.session_state.last_assistant)
    st.markdown("**Current project**")
    st.write(f"**Title:** {title or 'Untitled'}")
    st.write(f"**Format:** {project_type}")
    st.write(f"**Language:** {language}")
    st.write(f"**Genre:** {genre or 'Not specified'}")

if st.session_state.validation_report:
    st.markdown("### 🔎 Screenplay validation")
    for level, message in st.session_state.validation_report:
        if level == "error": st.error(message)
        elif level == "warning": st.warning(message)
        elif level == "success": st.success(message)
        else: st.info(message)

if st.session_state.script_text.strip():
    st.markdown("### Export screenplay")
    c1, c2 = st.columns(2)
    safe_name = "".join(ch for ch in (title or "screenplay") if ch.isalnum() or ch in "-_ ").strip().replace(" ", "_")
    with c1:
        st.download_button("Download DOCX", create_docx(st.session_state.script_text, title),
            file_name=f"{safe_name or 'screenplay'}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with c2:
        st.download_button("Download PDF", create_pdf(st.session_state.script_text, title),
            file_name=f"{safe_name or 'screenplay'}.pdf", mime="application/pdf")
    if st.session_state.script_before_doctor:
        with st.expander("Compare: original before Script Doctor"):
            st.text_area("Original screenplay", st.session_state.script_before_doctor, height=400)


if current_project_id is not None:
    save_project_workspace(
        current_project_id,
        screenplay=st.session_state.script_text,
        scene_plan=st.session_state.scene_plan,
        scene_plan_approved=st.session_state.scene_plan_approved,
        script_before_doctor=st.session_state.script_before_doctor,
        last_assistant=st.session_state.last_assistant,
    )
