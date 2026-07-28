# BridgeNote AI (PulseArk)

A lightweight real-time co-pilot for SEN (ASD) music volunteers. Equips
volunteers with a student sensory-profile card, an AI-generated visual lesson
routine, and an instant SOS de-escalation helper -- built as a weekend
"vibe coding" MVP prototype.

## Quick Start

```bash
cd "BridgeNote-AI"
pip install -r requirements.txt
streamlit run app.py
```
Opens automatically at http://localhost:8501

No API key is needed -- this prototype runs in **mock-AI mode**: `agent.py`
uses deterministic, ABA-informed templates instead of calling an LLM, so it
demos instantly, for free, with no risk of exposing a key.

## MVP Features (matches the PulseArk spec)

1. **Student Sensory Profile Card** -- communication style, sensory triggers,
   preferred reinforcers, and calming strategies for each student
   (`data/students.json`, 4 sample ASD violin students).
2. **AI Lesson Routine Builder** -- generates a 20-minute violin lesson
   broken into 3-5 minute micro-tasks, adapted to the student's attention
   span and preferred rewards. Rendered as a tappable checklist.
3. **Instant SOS Helper** -- three quick-select buttons ("Covering ears",
   "Refusing instrument", "Wanting to leave"). Each returns a 3-step
   de-escalation protocol personalized from that student's profile.
4. **Continuity log** -- lesson feedback and SOS events are saved to
   `data/session_log.json` so the next volunteer can pick up without
   starting from scratch.

## File Structure

```
BridgeNote-AI/
├── requirements.txt
├── .streamlit/config.toml   ← pastel theme + red SOS button color
├── data/
│   ├── students.json        ← mock student sensory profiles
│   └── session_log.json     ← created automatically once notes are saved
├── student_db.py             ← data access layer
├── agent.py                  ← Perceive→Reason→Act→Learn agent (rule-based)
└── app.py                    ← Streamlit UI
```

## Upgrading to a real LLM later

The public interface (`generate_lesson_routine`, `generate_sos_protocol` in
`agent.py`) is already the stable seam for this. To swap in real GPT-4o-mini
or Groq/Claude calls (as in the other PulseArk_AI phases -- see
`../Pulse Ark/PulseArk_AI/QUICKSTART.md`):

1. Add `python-dotenv` + `openai` (or `groq`) to `requirements.txt`.
2. Add your key to a local `.env` (never commit it).
3. Replace the body of `_generate_sos_steps` / `_generate_routine_blocks`
   with a prompt that feeds the same student profile + scenario into the
   model, keeping the existing function signatures so `app.py` doesn't
   need to change.

## Pilot Launch Notes (process, not code)

The 4-week pilot plan (parent onboarding in week 1, in-lesson testing in
weeks 2-3, evaluation in week 4) is a program-management workflow to run
with partner community centers/orchestras -- it isn't something this
prototype needs to implement in software.
