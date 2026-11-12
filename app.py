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
    "last_approved_blueprint": "",
    "last_generated_scene": "",
    "evaluation_report": None,
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

def call_ollama(system, user, model, temperature, max_tokens):
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

st.sidebar.markdown("### Project setup")
title = st.sidebar.text_input("Project title", placeholder="e.g. The Last Local Train")
project_type = st.sidebar.selectbox(
    "Screenplay format",
    ["Feature Film", "OTT / Web Series", "Short Film"],
    help="Choose the format for this project. You can start a different project in another format."
)
language = st.sidebar.text_input(
    "Writing language",
    value="English",
    help="Choose any language or mix, e.g. Hindi, Nepali, Hinglish, Malayalam, English with Hindi dialogue."
)
genre = st.sidebar.text_input("Genre", placeholder="Psychological thriller")
tone = st.sidebar.text_input("Tone", placeholder="Tense, grounded, atmospheric")
characters = st.sidebar.text_area("Main characters", placeholder="Name, age, personality, motivation…")
setting = st.sidebar.text_input("Primary setting", placeholder="Mumbai, present day")
logline = st.sidebar.text_area("Logline / premise", placeholder="What is the story about?")
notes = st.sidebar.text_area("Story notes / constraints", placeholder="Themes, plot points, restrictions…")
writing_style = st.sidebar.text_input("Style reference (optional)", placeholder="Describe qualities, not just a name")
trend_style = st.sidebar.text_input("Audience / genre convention (optional)")

st.sidebar.markdown("---")
generate_btn = st.sidebar.button("✍️ Generate Scene 1", use_container_width=True)
next_scene_btn = st.sidebar.button("＋ Generate Next Scene", use_container_width=True)
doctor_btn = st.sidebar.button("🩺 AI Script Doctor", use_container_width=True)
plan_opening_btn = st.sidebar.button("🧭 Plan Opening Scene", use_container_width=True)
plan_next_btn = st.sidebar.button("🧭 Plan Next Scene", use_container_width=True)
validate_btn = st.sidebar.button("🔎 Validate Screenplay", use_container_width=True)
evaluate_btn = st.sidebar.button("🧠 Evaluate Last Scene", use_container_width=True)

def project_context():
    return f"""PROJECT
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
from scene_evaluator import evaluate_scene

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
    st.session_state.last_approved_blueprint = st.session_state.scene_plan
    st.session_state.last_generated_scene = result
    st.session_state.evaluation_report = None
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
    st.session_state.last_approved_blueprint = st.session_state.scene_plan
    st.session_state.last_generated_scene = result
    st.session_state.evaluation_report = None
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

if evaluate_btn or st.session_state.pop("run_scene_evaluation", False):
    try:
        with st.spinner("Evaluating the last generated scene against its approved blueprint…"):
            st.session_state.evaluation_report = evaluate_scene(
                st.session_state.last_approved_blueprint,
                st.session_state.last_generated_scene,
                lambda system, prompt: call_ollama(system, prompt, model, 0.1, 1800),
            )
        st.session_state.last_assistant = "Evidence-based scene evaluation completed."
    except Exception as exc:
        st.error(f"Scene evaluation failed: {exc}")

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
st.caption(f"Local model: {model} · Format: {project_type} · Language: {language}")
left, right = st.columns([2, 1])
with left:
    st.subheader("📄 Screenplay")
    st.session_state.script_text = st.text_area(
        "Edit your screenplay here", value=st.session_state.script_text,
        height=650, label_visibility="collapsed",
        placeholder="Your screenplay will appear here. You can also paste or edit a draft."
    )
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
    if st.session_state.last_generated_scene:
        st.caption("Evaluate the most recently generated scene against the blueprint used to create it.")
        st.button("🧠 Evaluate Last Scene", key="evaluate_scene_panel", on_click=lambda: st.session_state.update({"run_scene_evaluation": True}))
    st.subheader("💬 Studio notes")
    if st.session_state.last_assistant:
        st.info(st.session_state.last_assistant)
    st.markdown("**Current project**")
    st.write(f"**Title:** {title or 'Untitled'}")
    st.write(f"**Format:** {project_type}")
    st.write(f"**Language:** {language}")
    st.write(f"**Genre:** {genre or 'Not specified'}")

if st.session_state.evaluation_report:
    report = st.session_state.evaluation_report
    st.markdown("### 🧠 Scene evaluation")
    st.metric("Average scene score", f"{report['average_score']} / 5")
    st.caption("LLM-as-a-judge assessment. Scores are editorial estimates, not objective measurements.")
    for criterion, item in report["criteria"].items():
        with st.expander(f"{criterion.replace('_', ' ').title()} — {item['score']}/5"):
            st.write(item["feedback"])
            if item["evidence"]:
                st.markdown("**Screenplay evidence**")
                st.quote(item["evidence"])
            else:
                st.caption("No supporting excerpt supplied.")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Strengths**")
        for item in report["strengths"]:
            st.write(f"• {item}")
    with col_b:
        st.markdown("**Improvements**")
        for item in report["improvements"]:
            st.write(f"• {item}")
    st.markdown("**Overall assessment**")
    st.write(report["overall_assessment"])

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
