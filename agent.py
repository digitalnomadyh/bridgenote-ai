"""
agent.py -- BridgeNote AI Co-Pilot Agent
Rule-based / template-driven agent (mock-AI mode -- no external LLM call).

Mirrors the Perceive -> Reason -> Act -> Learn pattern used by the other
PulseArk_AI phases (see phase1_playlist_curator/agent.py), but reasoning is
done with deterministic ABA-informed templates instead of an LLM call, so the
prototype runs instantly with zero API key and zero cost.

To upgrade later to a real LLM (e.g. GPT-4o-mini or Groq/llama), replace the
body of `_generate_sos_steps` / `_generate_routine_blocks` with a prompt that
feeds the same student profile + scenario into the model, keeping this
module's public functions (generate_sos_protocol, generate_lesson_routine) as
the stable interface the Streamlit UI already calls.
"""

from datetime import date

DISCLAIMER = (
    "This is general ABA-informed guidance for a volunteer co-pilot, not a clinical "
    "diagnosis or a substitute for the student's behavior support plan. If distress "
    "escalates or you are unsure, pause the session and get the supervising "
    "teacher/parent immediately."
)

SOS_SCENARIOS = ["Covering ears", "Refusing instrument", "Wanting to leave"]

STAGE_TEMPLATES = [
    {"type": "warm_up", "label": "Hello & Schedule Check-in"},
    {"type": "setup", "label": "Tuning & Instrument Hold"},
    {"type": "technique", "label": "Technique Drill"},
    {"type": "practice", "label": "Piece Practice"},
    {"type": "break", "label": "Sensory / Movement Break"},
    {"type": "practice", "label": "Piece Practice (Part 2)"},
    {"type": "cooldown", "label": "Cool-down & Choice Time"},
]


def _match_trigger(student: dict, keywords: list[str]) -> str:
    """Find the trigger most relevant to a scenario, falling back to the first one."""
    triggers = student.get("sensory_triggers", [])
    if not triggers:
        return "a known sensory trigger"
    for t in triggers:
        text = t["trigger"].lower()
        if any(k in text for k in keywords):
            return t["trigger"]
    return triggers[0]["trigger"]


def _generate_sos_steps(student: dict, scenario: str) -> dict:
    name = student["name"]
    comm = student["communication_style"]
    reinforcers = student["preferred_reinforcers"]
    calming = student["calming_strategies"]

    if scenario == "Covering ears":
        trigger = _match_trigger(student, ["pitch", "sound", "loud", "dynamic", "noise"])
        return {
            "principle": "Likely sensory overload from an auditory trigger. Reduce input first -- do not force continuation.",
            "steps": [
                f"Stop the current sound immediately (pause bowing/playing). Check if it involves \"{trigger}\", a known trigger for {name}.",
                f"Reduce auditory input: {calming[0]}.",
                f"Wait for hands to come down before re-engaging. Using {comm['type'].lower()} communication, offer a choice: continue quietly (e.g. pizzicato) or take a short break with \"{reinforcers[0]}\".",
            ],
        }

    if scenario == "Refusing instrument":
        return {
            "principle": "Likely escape/avoidance -- the task demand may be too high or the transition too abrupt. Repeating the same request tends to increase resistance.",
            "steps": [
                f"Stop repeating the request to pick up the instrument -- give {name} a few seconds of space instead.",
                f"Lower the demand using {comm['type'].lower()} communication: {comm['description']}",
                f"Reinforce any small step toward re-engagement right away with \"{reinforcers[0]}\" -- don't wait for full compliance.",
            ],
        }

    if scenario == "Wanting to leave":
        attention = student.get("attention_span_min", 4)
        return {
            "principle": f"{name}'s attention span for this task is roughly {attention} minutes -- this may simply be a need for movement or escape, not defiance.",
            "steps": [
                f"Do not physically block or force {name} to stay in the seat -- this can escalate into a bigger meltdown.",
                f"Honor the need with a structured option: {calming[0]}, timed with a visual timer if available.",
                f"Use {comm['type'].lower()} communication (e.g. a first/then board) to show what comes after the break, and offer \"{reinforcers[-1]}\" on return.",
            ],
        }

    return {
        "principle": "Unrecognized scenario.",
        "steps": ["Pause the activity.", "Consult the student's sensory profile card.", "Ask the supervising staff for guidance."],
    }


def _describe_stage(stage_type: str, student: dict) -> str:
    name = student["name"]
    comm = student["communication_style"]
    reinforcers = student["preferred_reinforcers"]
    calming = student["calming_strategies"]
    triggers = ", ".join(t["trigger"] for t in student["sensory_triggers"])

    if stage_type == "warm_up":
        return f"Show {name} today's schedule ({comm['type']} style). {comm['description']}"
    if stage_type == "setup":
        return f"Tune together and check bow/instrument hold. Watch for known triggers: {triggers}."
    if stage_type == "technique":
        return "Short bow-hold or pizzicato drill -- 1-2 repetitions only. Keep the demand small and end on success."
    if stage_type == "practice":
        return f"Practice the current piece in short phrases. Give {name} a structured choice of which section to play next."
    if stage_type == "break":
        return f"Offer a sensory reset: {calming[0]}, or a reinforcer break (\"{reinforcers[0]}\")."
    if stage_type == "cooldown":
        return f"Wrap up with {name}'s choice: \"{reinforcers[-1]}\". Mark today's schedule complete."
    return ""


def _generate_routine_blocks(student: dict, total_min: int = 20) -> list[dict]:
    attention = student.get("attention_span_min", 4)
    block_len = min(max(attention, 3), 5)

    n_blocks = min(max(4, round(total_min / block_len)), len(STAGE_TEMPLATES))
    chosen = STAGE_TEMPLATES[:n_blocks]

    routine = []
    elapsed = 0
    for i, stage in enumerate(chosen):
        is_last = i == len(chosen) - 1
        duration = (total_min - elapsed) if is_last else block_len
        duration = max(2, duration)
        routine.append({
            "order": i + 1,
            "title": stage["label"],
            "type": stage["type"],
            "duration_min": duration,
            "description": _describe_stage(stage["type"], student),
        })
        elapsed += duration
        if elapsed >= total_min:
            break
    return routine


class BridgeNoteAgent:
    """Perceive -> Reason -> Act -> Learn, backed by deterministic templates."""

    def perceive(self, student: dict) -> dict:
        return {"student": student}

    def reason_routine(self, student: dict) -> list[dict]:
        return _generate_routine_blocks(student)

    def reason_sos(self, student: dict, scenario: str) -> dict:
        return _generate_sos_steps(student, scenario)

    def act_routine(self, student: dict) -> dict:
        blocks = self.reason_routine(student)
        return {
            "student_id": student["id"],
            "generated_on": str(date.today()),
            "total_min": sum(b["duration_min"] for b in blocks),
            "blocks": blocks,
        }

    def act_sos(self, student: dict, scenario: str) -> dict:
        result = self.reason_sos(student, scenario)
        return {
            "student_id": student["id"],
            "scenario": scenario,
            "principle": result["principle"],
            "steps": result["steps"],
            "disclaimer": DISCLAIMER,
        }

    def learn(self, student_id: str, volunteer_name: str, note_type: str, note: str):
        from student_db import save_session_note
        save_session_note(student_id, volunteer_name, note_type, note)


def generate_lesson_routine(student: dict) -> dict:
    return BridgeNoteAgent().act_routine(student)


def generate_sos_protocol(student: dict, scenario: str) -> dict:
    return BridgeNoteAgent().act_sos(student, scenario)
