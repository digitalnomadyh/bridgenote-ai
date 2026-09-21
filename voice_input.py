"""
voice_input.py -- dictation widget for BridgeNote AI.

Streamlit has no built-in speech-to-text, and the browser's Web Speech API has
to run client-side, so this is a tiny custom component (plain HTML/JS in
voice_input_component/, no build step). It sends each finished phrase back to
Python as {"id", "text", "lang"}; `append_dictation` adds it to a text area.
"""

import os

import streamlit as st
import streamlit.components.v1 as components

_component = components.declare_component(
    "bridgenote_voice_input",
    path=os.path.join(os.path.dirname(__file__), "voice_input_component"),
)


def append_dictation(text_key: str, component_key: str = "voice_input") -> None:
    """Render the mic widget and append new phrases to st.session_state[text_key].

    Call this *before* creating the st.text_area(key=text_key), so the updated
    value is picked up in the same run.
    """
    phrase = _component(key=component_key, default=None)
    # The component keeps returning its last value on every rerun, so de-dupe by id.
    if phrase and phrase.get("id") != st.session_state.get(f"{component_key}_last_id"):
        st.session_state[f"{component_key}_last_id"] = phrase["id"]
        previous = st.session_state.get(text_key, "").rstrip()
        st.session_state[text_key] = f"{previous} {phrase['text']}".strip()
