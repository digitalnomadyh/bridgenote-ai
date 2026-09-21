"""
app.py -- BridgeNote AI Streamlit App
Run: streamlit run app.py

Equips music volunteers with a student sensory-profile card, an AI-generated
visual lesson routine, and an instant SOS de-escalation helper.
Mock-AI mode: all "AI" output comes from deterministic ABA-informed templates
in agent.py -- no external API key required.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import importlib

import streamlit as st

# Streamlit Cloud does not watch files, so a redeploy keeps the *old* copy of any local module
# that was already imported. Reload them on every run so pushes take effect without a reboot.
for _mod in ("student_db", "agent", "lesson_timer", "voice_input"):
    if _mod in sys.modules:
        importlib.reload(sys.modules[_mod])

from agent import BridgeNoteAgent, generate_lesson_routine, generate_sos_protocol, SOS_SCENARIOS
from student_db import load_students, get_notes_for_student
from lesson_timer import render_lesson_timer
from voice_input import append_dictation

st.set_page_config(
    page_title="BridgeNote AI -- PulseArk",
    page_icon="🎻",
    layout="wide",
)

agent = BridgeNoteAgent()

st.markdown("""
<style>
.profile-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    margin-bottom: 8px;
}
.chip {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    margin: 3px 4px 3px 0;
}
.chip-trigger { background: #FFE3E3; color: #B5495B; }
.chip-reward { background: #E3F6E5; color: #2E7D4F; }
.chip-calm { background: #E3EEFF; color: #2E5C9A; }
.routine-block {
    background: #ffffff;
    border-left: 6px solid #B9AFFF;
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 8px;
}
.stage-break { border-left-color: #FFD08A; }
.stage-cooldown { border-left-color: #9AD0C2; }
.stage-showcase { border-left-color: #FF8FA3; }
</style>
""", unsafe_allow_html=True)

STAGE_CLASS = {"break": "stage-break", "cooldown": "stage-cooldown", "showcase": "stage-showcase"}


@st.dialog("🆘 Instant SOS Helper")
def sos_dialog(student: dict, volunteer_name: str):
    st.write(f"What's happening with **{student['name']}** right now?")
    cols = st.columns(3)
    for col, scenario in zip(cols, SOS_SCENARIOS):
        if col.button(scenario, use_container_width=True, key=f"sos_btn_{scenario}"):
            st.session_state["active_sos_scenario"] = scenario

    chosen = st.session_state.get("active_sos_scenario")
    if chosen:
        result = generate_sos_protocol(student, chosen)
        st.divider()
        st.error(f"Scenario: {chosen}")
        st.markdown(f"**Likely cause:** {result['principle']}")
        for i, step in enumerate(result["steps"], 1):
            st.markdown(f"**Step {i}.** {step}")
        st.caption(f"⚠️ {result['disclaimer']}")

        note = st.text_area("Log what happened (optional -- helps the next volunteer)", key="sos_note")
        if st.button("💾 Save to continuity log", type="primary"):
            log_text = f"[{chosen}] {note}" if note else f"[{chosen}] SOS triggered, followed protocol."
            agent.learn(student["id"], volunteer_name, "sos_event", log_text)
            st.success("Saved to continuity log.")
            del st.session_state["active_sos_scenario"]
            st.rerun()

    if st.button("Close"):
        st.session_state.pop("active_sos_scenario", None)
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("## 🎻")
with col_title:
    st.markdown("## BridgeNote AI")
    st.caption("PulseArk · A real-time co-pilot for SEN music volunteers")

st.divider()

# ── Session setup ────────────────────────────────────────────────────────
students = load_students()
setup_col1, setup_col2 = st.columns([2, 2])
with setup_col1:
    student_names = {s["name"]: s for s in students}
    selected_name = st.selectbox("Today's Student", list(student_names.keys()))
    student = student_names[selected_name]
with setup_col2:
    volunteer_name = st.text_input("Your Name (volunteer)", placeholder="e.g. Sarah")

st.divider()

# ── Student Sensory Profile Card ─────────────────────────────────────────
st.subheader("① Student Sensory Profile Card")

triggers_html = "".join(f'<span class="chip chip-trigger">⚡ {t["trigger"]}</span>' for t in student["sensory_triggers"])
rewards_html = "".join(f'<span class="chip chip-reward">🎁 {r}</span>' for r in student["preferred_reinforcers"])
calm_html = "".join(f'<span class="chip chip-calm">🌿 {c}</span>' for c in student["calming_strategies"])

st.markdown(f"""
<div class="profile-card">
<h4>{student['name']}, age {student['age']} · {student['instrument']} · {student['diagnosis']}</h4>
<p><b>Communication style:</b> {student['communication_style']['type']} -- {student['communication_style']['description']}</p>
<p><b>Attention span:</b> ~{student['attention_span_min']} minutes per task</p>
<p><b>Sensory triggers:</b><br>{triggers_html}</p>
<p><b>Preferred reinforcers:</b><br>{rewards_html}</p>
<p><b>Calming strategies:</b><br>{calm_html}</p>
</div>
""", unsafe_allow_html=True)

with st.expander("📚 Continuity notes from previous volunteers"):
    notes = get_notes_for_student(student["id"])
    if not notes:
        st.info("No notes logged yet for this student.")
    else:
        for n in notes:
            icon = "🆘" if n["note_type"] == "sos_event" else "📝"
            st.markdown(f"{icon} **{n['timestamp']}** · {n['volunteer_name']} -- {n['note']}")

st.divider()

# ── AI Lesson Routine Builder ────────────────────────────────────────────
st.subheader("② AI Lesson Routine Builder")
st.caption("Generates a minute-by-minute visual schedule tailored to this student's attention span and rewards.")

gen_col, _ = st.columns([2, 6])
with gen_col:
    if st.button("🗓️ Generate Today's Routine", type="primary", use_container_width=True):
        st.session_state["routine"] = generate_lesson_routine(student)

routine = st.session_state.get("routine")
if routine and routine["student_id"] == student["id"]:
    st.metric("Total Session Length", f"{routine['total_min']} min")

    st.markdown("**⏱️ Lesson timer** -- press Start when the lesson begins. A soft beep tells you when to move to the next step.")
    demo_speed = st.checkbox("Demo speed (1 min = 5 sec, for trying it out)", key="timer_demo_speed")
    render_lesson_timer(routine, seconds_per_minute=5 if demo_speed else 60)

    for block in routine["blocks"]:
        css_class = STAGE_CLASS.get(block["type"], "")
        check_key = f"check_{student['id']}_{block['order']}"
        checked = st.checkbox(
            f"**{block['order']}. {block['title']}** ({block['duration_min']} min)",
            key=check_key,
        )
        st.markdown(f"""<div class="routine-block {css_class}">{block['description']}</div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("**Lesson feedback for the next volunteer (optional)** -- type, or tap the mic and dictate.")
    append_dictation("lesson_feedback", component_key="feedback_voice")
    feedback = st.text_area("Lesson feedback", key="lesson_feedback", label_visibility="collapsed")
    if st.button("💾 Save lesson feedback"):
        if feedback:
            agent.learn(student["id"], volunteer_name, "lesson_feedback", feedback)
            st.success("Feedback saved to continuity log.")
        else:
            st.warning("Write a short note before saving.")
else:
    st.info("Click 'Generate Today's Routine' to build a visual, minute-by-minute plan for this student.")

st.divider()

# ── Instant SOS Helper ───────────────────────────────────────────────────
st.subheader("③ Instant SOS Helper")
st.caption("Tap for a 3-step de-escalation protocol based on this student's sensory profile.")

sos_col, _ = st.columns([2, 6])
with sos_col:
    if st.button("🆘 SOS -- I need help now", type="primary", use_container_width=True):
        sos_dialog(student, volunteer_name)

st.markdown("---")
st.caption("BridgeNote AI · PulseArk · Mock-AI mode (rule-based) -- no external API key required for this prototype.")
