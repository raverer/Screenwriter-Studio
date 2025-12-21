# app.py — Screenwriter Studio (Groq Final)
# Stable, fast, Streamlit Cloud ready

import os
import html
import streamlit as st
from groq import Groq

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
# Models (SAFE)
# ===============================
GROQ_MODEL = "llama-3.1-8b-instant"  # safest for Streamlit Cloud

# ===============================
# Session defaults
# ===============================
st.session_state.setdefault("script_text", "")
st.session_state.setdefault("last_assistant", "")

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
# System prompt (SHORT, SAFE)
# ===============================
SYSTEM_PROMPT = (
    "You are a professional screenwriter. "
    "Write in standard screenplay format using INT./EXT., ACTION, CHARACTER, DIALOGUE. "
    "Maintain story logic and pacing. "
    "Output only the screenplay text."
)

# ===============================
# Groq call (CORRECT API)
# ===============================
def call_groq(system_prompt: str, user_prompt: str) -> str:
    try:
        response = client.responses.create(
            model=GROQ_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt[-4000:]},
            ],
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return response.output_text.strip()

    except Exception as e:
        st.error("Groq request failed. Try generating scene by scene.")
        raise e

# ===============================
# Generation logic
# ===============================
def generate_scene_1():
    prompt = f"""
Title: {title}
Genre: {genre}
Tone: {tone}
Characters: {characters}
Setting: {setting}
Notes: {notes}
Writing style: {writing_style or "cinematic"}

Write ONLY SCENE 1 of a short film.
Start with FADE IN.
Do not write more than one scene.
"""
    with st.spinner("Generating Scene 1…"):
        result = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.script_text = result
    st.session_state.last_assistant = result


def generate_next_scene():
    prompt = f"""
Continue the screenplay with the NEXT scene only.
Do not repeat previous scenes.

SCREENPLAY SO FAR:
{st.session_state.script_text[-4000:]}
"""
    with st.spinner("Generating next scene…"):
        result = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.script_text += "\n\n" + result
    st.session_state.last_assistant = result


def run_script_doctor():
    prompt = f"""
Analyze the following screenplay.
Improve pacing, dialogue, and character motivation.
Rewrite ONLY the weak sections.

SCRIPT:
{st.session_state.script_text}
"""
    with st.spinner("Running AI Script Doctor…"):
        result = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.last_assistant = result

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

st.caption("⚡ Powered by Groq · LLaMA-3.1")
