"""
lesson_timer.py -- in-lesson countdown timer for BridgeNote AI.

Streamlit reruns the whole script on every click, so a timer has to live in the
browser. This renders a small self-contained HTML/JS widget (Web Audio for the
beep) that walks through the routine blocks and prompts the volunteer to move
on when each block's time is up.

Sound is deliberately soft and low-pitched: many SEN students are sensitive to
sharp or high-pitched tones, so a mute toggle is always available and the
prompt is also shown visually (and via vibration where supported).
"""

import json

import streamlit.components.v1 as components

_TEMPLATE = """
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Source Sans Pro", system-ui, sans-serif; color: #3b3a4a; }
  .wrap { background: #fff; border-radius: 16px; padding: 18px 22px;
          box-shadow: 0 2px 10px rgba(0,0,0,.06); transition: background .4s; }
  .wrap.flash { background: #FFF3D6; }
  .wrap.done { background: #E3F6E5; }
  .top { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }
  .step { font-size: 1.05rem; font-weight: 600; }
  .clock { font-size: 3rem; font-weight: 700; letter-spacing: 1px; font-variant-numeric: tabular-nums; }
  .desc { margin: 6px 0 12px; color: #5c5b6e; min-height: 2.6em; }
  .banner { display: none; margin: 0 0 12px; padding: 10px 14px; border-radius: 10px;
            background: #FFE3B0; color: #7a4a00; font-weight: 600; }
  .banner.show { display: block; }
  .bar { display: flex; gap: 4px; margin-bottom: 14px; }
  .seg { height: 10px; border-radius: 5px; background: #E6E3F5; overflow: hidden; }
  .seg > i { display: block; height: 100%; width: 0; background: #B9AFFF; }
  .seg.past > i { width: 100%; background: #9AD0C2; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; }
  button { border: 0; border-radius: 10px; padding: 10px 16px; font-size: .95rem; cursor: pointer;
           background: #EEEBFF; color: #3b3a4a; }
  button.primary { background: #FF6B6B; color: #fff; font-weight: 600; }
  button:disabled { opacity: .45; cursor: default; }
  .next { color: #8a889c; font-size: .9rem; margin-top: 10px; }
</style>

<div class="wrap" id="wrap">
  <div class="top">
    <div class="step" id="step"></div>
    <div class="clock" id="clock">00:00</div>
  </div>
  <div class="desc" id="desc"></div>
  <div class="banner" id="banner"></div>
  <div class="bar" id="bar"></div>
  <div class="row">
    <button class="primary" id="start">&#9654; Start lesson</button>
    <button id="pause" disabled>&#9208; Pause</button>
    <button id="skip" disabled>&#9197; Next step</button>
    <button id="reset">&#8634; Reset</button>
    <button id="sound">&#128266; Sound on</button>
  </div>
  <div class="next" id="next"></div>
</div>

<script>
const BLOCKS = __BLOCKS__;
const SEC_PER_MIN = __SEC_PER_MIN__;
const el = id => document.getElementById(id);

let idx = 0, remaining = 0, running = false, endAt = 0, started = false, finished = false;
let soundOn = true, ctx = null, wakeLock = null, bannerTimer = null;

const durMs = i => BLOCKS[i].duration_min * SEC_PER_MIN * 1000;

// ---- audio: soft, low sine beeps (kind to sound-sensitive students) --------
function beep(times, freq, len) {
  if (!soundOn || !ctx) return;
  for (let n = 0; n < times; n++) {
    const t0 = ctx.currentTime + n * (len + 0.18);
    const osc = ctx.createOscillator(), g = ctx.createGain();
    osc.type = "sine"; osc.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(0.12, t0 + 0.04);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + len);
    osc.connect(g); g.connect(ctx.destination);
    osc.start(t0); osc.stop(t0 + len + 0.02);
  }
}
function buzz() { try { navigator.vibrate && navigator.vibrate([180, 90, 180]); } catch (e) {} }

async function keepAwake() {
  try { if (navigator.wakeLock && running) wakeLock = await navigator.wakeLock.request("screen"); } catch (e) {}
}
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") { keepAwake(); tick(); } });

// ---- rendering ------------------------------------------------------------
function fmt(ms) {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
}
function buildBar() {
  el("bar").innerHTML = "";
  BLOCKS.forEach((b, i) => {
    const seg = document.createElement("div");
    seg.className = "seg"; seg.style.flex = b.duration_min; seg.id = "seg" + i;
    seg.title = b.order + ". " + b.title;
    seg.appendChild(document.createElement("i"));
    el("bar").appendChild(seg);
  });
}
function render() {
  const b = BLOCKS[idx];
  el("step").textContent = finished ? "Lesson complete" : b.order + " / " + BLOCKS.length + " · " + b.title;
  el("desc").textContent = finished ? "Nice work! Remember to save lesson feedback for the next volunteer below." : b.description;
  el("clock").textContent = finished ? "00:00" : fmt(running ? endAt - Date.now() : remaining);
  const nb = BLOCKS[idx + 1];
  el("next").textContent = finished ? "" : (nb ? "Up next: " + nb.title + " (" + nb.duration_min + " min)" : "Last step of the lesson");
  BLOCKS.forEach((_, i) => {
    const seg = el("seg" + i);
    seg.className = "seg" + (finished || i < idx ? " past" : "");
    const fill = seg.firstChild;
    if (!finished && i === idx) {
      const left = running ? endAt - Date.now() : remaining;
      fill.style.width = (100 - Math.max(0, left) / durMs(i) * 100) + "%";
    } else fill.style.width = "";
  });
  el("wrap").classList.toggle("done", finished);
  el("pause").disabled = !started || finished;
  el("skip").disabled = !started || finished;
  el("pause").innerHTML = (running || !started || finished) ?"&#9208; Pause" : "&#9654; Resume";
  el("start").disabled = started;
}
function announce(text) {
  el("banner").textContent = text; el("banner").classList.add("show");
  el("wrap").classList.add("flash");
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => { el("banner").classList.remove("show"); el("wrap").classList.remove("flash"); }, 8000);
}

// ---- timer core -----------------------------------------------------------
function goTo(i, cueNow) {
  if (i >= BLOCKS.length) {
    finished = true; running = false; started = true;
    if (cueNow) { beep(3, 392, 0.35); buzz(); }
    announce("Lesson time is up. Great job!");
    render(); return;
  }
  idx = i; remaining = durMs(i);
  if (running) endAt = Date.now() + remaining;
  if (cueNow) { beep(2, 440, 0.25); buzz(); announce("Time to move on → " + BLOCKS[i].order + ". " + BLOCKS[i].title); }
  render();
}
function tick() {
  if (!running) return;
  // catch up if the tab was throttled and several steps elapsed
  let cue = false;
  while (running && Date.now() >= endAt) {
    const carry = endAt;
    cue = true;
    if (idx + 1 >= BLOCKS.length) { goTo(BLOCKS.length, true); return; }
    idx++; remaining = durMs(idx); endAt = carry + remaining;
  }
  if (cue) { beep(2, 440, 0.25); buzz(); announce("Time to move on → " + BLOCKS[idx].order + ". " + BLOCKS[idx].title); }
  render();
}

el("start").onclick = () => {
  if (!ctx) { try { ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} }
  if (ctx && ctx.state === "suspended") ctx.resume();
  started = true; running = true; endAt = Date.now() + remaining;
  beep(1, 440, 0.2); keepAwake(); render();
};
el("pause").onclick = () => {
  if (running) { remaining = endAt - Date.now(); running = false; try { wakeLock && wakeLock.release(); } catch (e) {} }
  else { running = true; endAt = Date.now() + remaining; keepAwake(); }
  render();
};
el("skip").onclick = () => { goTo(idx + 1, false); if (running) el("banner").classList.remove("show"); };
el("reset").onclick = () => {
  running = false; started = false; finished = false;
  try { wakeLock && wakeLock.release(); } catch (e) {}
  el("banner").classList.remove("show"); el("wrap").classList.remove("flash");
  goTo(0, false);
};
el("sound").onclick = () => {
  soundOn = !soundOn;
  el("sound").innerHTML = soundOn ? "&#128266; Sound on" : "&#128263; Sound off (visual only)";
};

buildBar(); goTo(0, false);
setInterval(() => { tick(); }, 250);
</script>
"""


def render_lesson_timer(routine: dict, seconds_per_minute: int = 60) -> None:
    """Render the countdown widget for a routine from agent.generate_lesson_routine."""
    blocks = [
        {
            "order": b["order"],
            "title": b["title"],
            "duration_min": b["duration_min"],
            "description": b["description"],
        }
        for b in routine["blocks"]
    ]
    # "</" would end the <script> tag early if a description ever contained it
    blocks_json = json.dumps(blocks).replace("</", "<\\/")
    html = _TEMPLATE.replace("__BLOCKS__", blocks_json).replace("__SEC_PER_MIN__", str(int(seconds_per_minute)))
    components.html(html, height=330)
