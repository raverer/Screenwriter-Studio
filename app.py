# app.py — Screenwriter Studio
# Streamlit screenplay writing app powered by Groq.

import os
import html
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

import streamlit as st
from groq import Groq
from docx import Document
from docx.shared import Pt, Inches
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Preformatted, Spacer, Paragraph

# ===============================
# Page config
# ===============================
st.set_page_config(
    page_title="Screenwriter Studio",
    layout="wide",
)

# ===============================
# Groq client
# ===============================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY not found. Set it in Streamlit secrets or environment.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# ===============================
# Model configuration
# ===============================
GROQ_MODEL = "llama-3.1-8b-instant"

# ===============================
# Session defaults
# ===============================
st.session_state.setdefault("script_text", "")
st.session_state.setdefault("last_assistant", "")
st.session_state.setdefault("script_before_doctor", "")

# ===============================
# Sidebar UI
# ===============================
st.sidebar.title("🎬 Screenwriter Studio")

temperature = st.sidebar.slider("Temperature", 0.1, 1.2, 0.7)
max_tokens = st.sidebar.slider("Max output tokens", 256, 768, 512, step=128)

st.sidebar.markdown("### Metadata")
title = st.sidebar.text_input("Title / Idea")
genre = st.sidebar.text_input("Genre")
tone = st.sidebar.text_input("Tone / Style")
characters = st.sidebar.text_input("Characters")
setting = st.sidebar.text_input("Setting")
notes = st.sidebar.text_area("Notes")

writing_style = st.sidebar.text_input("Writing Style (optional)")
trend_style = st.sidebar.text_input("Trend / Viral Style (optional)")

st.sidebar.markdown("---")
generate_btn = st.sidebar.button("Generate Scene 1")
next_scene_btn = st.sidebar.button("Generate Next Scene")
doctor_btn = st.sidebar.button("AI Script Doctor")

# ===============================
# System prompt
# ===============================
SYSTEM_PROMPT = (
    "You are a professional screenwriter. "
    "Write in standard screenplay format using INT./EXT., ACTION, CHARACTER, and DIALOGUE. "
    "Maintain story logic, character continuity, visual storytelling, and pacing. "
    "Output only the requested screenplay text."
)

# ===============================
# Groq call
# ===============================
def call_groq(system: str, user: str) -> str:
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system[:1000]},
                {"role": "user", "content": user[-12000:]},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        response = completion.choices[0].message.content
        if not response or not response.strip():
            raise ValueError("The model returned an empty response.")
        return response.strip()
    except Exception as exc:
        st.error(f"Groq request failed: {exc}")
        raise

# ===============================
# Export helpers
# ===============================
def create_docx(script: str) -> bytes:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(1.2)
    section.right_margin = Inches(1.0)

    normal = document.styles["Normal"]
    normal.font.name = "Courier New"
    normal.font.size = Pt(10)

    if title.strip():
        heading = document.add_heading(title.strip(), level=1)
        for run in heading.runs:
            run.font.name = "Courier New"

    for line in script.splitlines():
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(line if line else " ")
        run.font.name = "Courier New"
        run.font.size = Pt(10)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def create_pdf(script: str) -> bytes:
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=1.0 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=title.strip() or "Screenplay",
    )
    screenplay_style = ParagraphStyle(
        "Screenplay",
        fontName="Courier",
        fontSize=8.5,
        leading=11,
    )
    safe_script = xml_escape(script)
    story = []
    if title.strip():
        story.append(Paragraph(xml_escape(title.strip()), ParagraphStyle(
            "DocumentTitle", parent=screenplay_style, fontSize=14, leading=18
        )))
        story.append(Spacer(1, 0.2 * inch))
    story.append(Preformatted(safe_script, screenplay_style, maxLineLength=88))
    pdf.build(story)
    return buffer.getvalue()


# ===============================
# Generation logic
# ===============================
def generate_scene_1():
    prompt = f"""
Project details:
Title: {title}
Genre: {genre}
Tone: {tone}
Characters: {characters}
Setting: {setting}
Notes: {notes}
Writing style: {writing_style or "cinematic"}
Trend / viral reference: {trend_style or "None"}

Write ONLY SCENE 1 of a short film.
Start with FADE IN.
Do not write more than one scene.
Use screenplay format.
"""
    with st.spinner("Generating Scene 1…"):
        result = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.script_text = result
    st.session_state.last_assistant = result


def generate_next_scene():
    if not st.session_state.script_text.strip():
        st.warning("Generate Scene 1 before asking for the next scene.")
        return

    prompt = f"""
Continue the screenplay with the NEXT scene only.
Do not repeat previous scenes. Maintain character, plot, location,
and timeline continuity. End at a natural transition point.

SCREENPLAY SO FAR:
{st.session_state.script_text[-10000:]}
"""
    with st.spinner("Generating next scene…"):
        result = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.script_text += "\n\n" + result
    st.session_state.last_assistant = result


def run_script_doctor():
    current_script = st.session_state.script_text.strip()
    if not current_script:
        st.warning("Generate or enter a screenplay before using AI Script Doctor.")
        return

    prompt = f"""
Act as a screenplay editor and script doctor.

Review the screenplay for:
- Story structure, pacing, and scene progression
- Character motivation, consistency, and development
- Dialogue naturalness and subtext
- Visual storytelling and cinematic action
- Repetition, plot gaps, and continuity errors

Then provide a COMPLETE revised version of the screenplay, not notes,
not a list of suggestions, and not only selected excerpts.
Preserve the original premise, intended tone, characters, and all important
story events unless a change is necessary to fix a clear story problem.
Keep standard screenplay formatting. Do not invent a new story.

SCREENPLAY TO REVISE:
{current_script}
"""
    with st.spinner("Reviewing and revising the complete screenplay…"):
        revised_script = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.script_before_doctor = current_script
    st.session_state.script_text = revised_script
    st.session_state.last_assistant = (
        "AI Script Doctor completed a full screenplay revision. "
        "The revised version is now shown in the screenplay panel."
    )
    st.success("The revised screenplay has replaced the previous version. The original is retained in this session.")

# ===============================
# Button actions
# ===============================
if generate_btn:
    generate_scene_1()

if next_scene_btn:
    generate_next_scene()

if doctor_btn:
    run_script_doctor()

# ===============================
# Main layout
# ===============================
left, right = st.columns([2, 1])

with left:
    st.subheader("📄 Screenplay")
    if st.session_state.script_text:
        safe_text = html.escape(st.session_state.script_text).replace("\n", "<br>")
        st.markdown(
            f"<div style='font-family:Courier New, monospace; font-size:14px'>{safe_text}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("No screenplay yet.")

with right:
    st.subheader("💬 Assistant Output")
    if st.session_state.last_assistant:
        safe_chat = html.escape(st.session_state.last_assistant).replace("\n", "<br>")
        st.markdown(safe_chat, unsafe_allow_html=True)
    else:
        st.caption("No assistant output yet.")

# ===============================
# Download controls
# ===============================
if st.session_state.script_text.strip():
    st.markdown("### Export screenplay")
    export_col1, export_col2 = st.columns(2)

    with export_col1:
        docx_data = create_docx(st.session_state.script_text)
        st.download_button(
            label="Download DOCX",
            data=docx_data,
            file_name=f"{title.strip() or 'screenplay'}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    with export_col2:
        pdf_data = create_pdf(st.session_state.script_text)
        st.download_button(
            label="Download PDF",
            data=pdf_data,
            file_name=f"{title.strip() or 'screenplay'}.pdf",
            mime="application/pdf",
        )

    if st.session_state.script_before_doctor:
        with st.expander("View original screenplay before Script Doctor"):
            st.text(st.session_state.script_before_doctor)

st.caption(f"⚡ Powered by Groq · {GROQ_MODEL}")
