"""
lesson_timer.py -- in-lesson countdown timer (and optional device-only video recording)
for BridgeNote AI.

Streamlit reruns the whole script on every click, so a timer has to live in the
browser. It is a small build-free custom component (lesson_timer_component/index.html:
HTML/JS, Web Audio for the beep, MediaRecorder for the optional recording) that walks
through the routine blocks and prompts the volunteer to move on when each block's
time is up.

Sound is deliberately soft and low-pitched: many SEN students are sensitive to
sharp or high-pitched tones, so a mute toggle is always available and the
prompt is also shown visually (and via vibration where supported).

The last block ("Show What You Learned") offers to record the student playing. The
video is created in the browser and saved to the volunteer's own device only --
it is never sent to the server -- and needs an explicit guardian-consent tick.
"""

import os

import streamlit.components.v1 as components

_component = components.declare_component(
    "bridgenote_lesson_timer",
    path=os.path.join(os.path.dirname(__file__), "lesson_timer_component"),
)


def render_lesson_timer(routine: dict, seconds_per_minute: int = 60) -> None:
    """Render the countdown widget for a routine from agent.generate_lesson_routine."""
    blocks = [
        {
            "order": b["order"],
            "title": b["title"],
            "duration_min": b["duration_min"],
            "type": b["type"],
            "description": b["description"],
        }
        for b in routine["blocks"]
    ]
    # Same key on every run: args changes restart the timer inside the browser, reruns do not.
    _component(
        blocks=blocks,
        sec_per_min=int(seconds_per_minute),
        student=routine.get("student_id", "student"),
        key="lesson_timer",
        default=None,
    )
