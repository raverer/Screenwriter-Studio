# app.py — Screenwriter Studio (Groq Final)
# Stable, fast, Streamlit Cloud ready

import os
import re
import json
import html
from datetime import datetime
from typing import Any, List, Dict, Iterable, Optional

import streamlit as st
from groq import Groq

# ===============================
# Page config
# ===============================
st.set_page_config(page_title="Screenwriter Studio", layout="wide")

# ===============================
# Groq client
# ===============================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY not found. Set it in environment variables or Streamlit secrets.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# ===============================
# Groq model mapping (UPDATED)
# ===============================
GROQ_FAST_MODEL = "llama-3.1-8b-instant"
GROQ_LONG_MODEL = "llama-3.1-70b-versatile"

def trim_prompt(text: str, max_chars: int = 12000) -> str:
    """
    Groq-safe prompt trimming.
    Uses character count instead of tokens for speed & safety.
    """
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]

def pick_model_for_generation(prompt: str) -> str:
    return GROQ_FAST_MODEL if len(prompt) < 300 else GROQ_LONG_MODEL

# ===============================
# Session defaults
# ===============================
defaults = {
    "script_text": "",
    "story_outline": "",
    "chat_history": [],
    "last_assistant": "",
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ===============================
# UI — Sidebar
# ===============================
st.sidebar.title("🎬 Screenwriter Studio")

temperature = st.sidebar.slider("Temperature", 0.1, 1.2, 0.7)
max_tokens = st.sidebar.slider("Max tokens", 512, 4096, 2048, step=256)

st.sidebar.markdown("### Metadata")
title = st.sidebar.text_input("Title / Idea")
genre = st.sidebar.text_input("Genre")
tone = st.sidebar.text_input("Tone / Style")
characters = st.sidebar.text_input("Characters")
setting = st.sidebar.text_input("Setting")
notes = st.sidebar.text_area("Notes")

script_format = st.sidebar.selectbox(
    "Script Format",
    ["Short Film", "Social Media Viral Short (30–90s)"]
)

writing_style = st.sidebar.text_input("Writing Style (optional)")
trend_style = st.sidebar.text_input("Trend / Viral Style (optional)")

st.sidebar.markdown("---")
generate_btn = st.sidebar.button("Generate Script")
next_scene_btn = st.sidebar.button("Generate Next Scene")
script_doctor_btn = st.sidebar.button("AI Script Doctor")

# ===============================
# System prompt (SHORT & FAST)
# ===============================
SYSTEM_PROMPT = """
You are a professional screenwriter.
Write clean, cinematic screenplays using proper format:
INT./EXT., ACTION, CHARACTER, DIALOGUE.
Maintain logic, pacing, emotional arcs.
Do not explain. Output only screenplay text.
"""

# ===============================
# Groq call (NO chat history feeding)
# ===============================
def call_groq(system: str, user: str) -> str:
    model = pick_model_for_generation(user)

    # HARD SAFE LIMITS (Groq-tested)
    SAFE_SYSTEM_CHARS = 2000
    SAFE_USER_CHARS = 6000
    SAFE_MAX_TOKENS = 512

    system = system[-SAFE_SYSTEM_CHARS:]
    user = user[-SAFE_USER_CHARS:]

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=SAFE_MAX_TOKENS,
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        # Show readable error instead of crashing
        st.error("Groq request failed. Try reducing prompt size or regenerating.")
        raise e



# ===============================
# Prompt builders
# ===============================
def shortfilm_prompt():
    return f"""
Title: {title}
Genre: {genre}
Tone: {tone}
Characters: {characters}
Setting: {setting}
Notes: {notes}
Writing style: {writing_style or "cinematic"}

Write a COMPLETE short film screenplay from FADE IN to FADE OUT.
Do not stop early.
"""

def viral_prompt():
    return f"""
Title: {title}
Genre: {genre}
Tone: {tone}
Characters: {characters}
Setting: {setting}
Trend style: {trend_style}
Writing style: {writing_style}

Write a 30–90 second viral video script.
Include hook, build, punchline, loopable ending.
Add caption + hashtags.
"""

# ===============================
# Generation logic
# ===============================
def generate_script():
    if "Social Media" in script_format:
        prompt = viral_prompt()
    else:
        prompt = shortfilm_prompt()

    with st.spinner("Generating script…"):
        result = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.script_text = result
    st.session_state.last_assistant = result

def generate_next_scene():
    prompt = f"""
Continue the screenplay below with the NEXT logical scene.
Do not repeat scenes.

SCREENPLAY:
{st.session_state.script_text}
"""
    with st.spinner("Generating next scene…"):
        out = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.script_text += "\n\n" + out
    st.session_state.last_assistant = out

def run_script_doctor():
    prompt = f"""
Analyze and improve this screenplay.
Fix pacing, dialogue, character motivation.
Then rewrite only the weak sections.

SCRIPT:
{st.session_state.script_text}
"""
    with st.spinner("Running AI Script Doctor…"):
        out = call_groq(SYSTEM_PROMPT, prompt)

    st.session_state.last_assistant = out

# ===============================
# Button actions
# ===============================
if generate_btn:
    generate_script()

if next_scene_btn:
    generate_next_scene()

if script_doctor_btn:
    run_script_doctor()

# ===============================
# Main layout
# ===============================
left, right = st.columns([2, 1])

with left:
    st.subheader("📄 Screenplay")
    safe_text = html.escape(st.session_state.script_text).replace("\n", "<br>")
    st.markdown(f"<div style='font-family:monospace'>{safe_text}</div>", unsafe_allow_html=True)

with right:
    st.subheader("💬 Assistant Output")
    if st.session_state.last_assistant:
        safe_chat = html.escape(st.session_state.last_assistant).replace("\n", "<br>")
        st.markdown(safe_chat, unsafe_allow_html=True)
    else:
        st.caption("No assistant output yet.")

st.caption("⚡ Powered by Groq LLaMA-3.1")
