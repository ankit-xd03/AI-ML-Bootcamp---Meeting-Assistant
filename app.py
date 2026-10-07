import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import difflib
import html
import inspect
import io
import json
import re
import tempfile
import time
import zipfile

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pipeline.export import save_outputs, to_markdown
from pipeline.mascot import show_mascot
from pipeline.run import process_audio
from pipeline.stt import SUPPORTED, AudioError

st.set_page_config(page_title="TalkToTasks", page_icon="🔝", layout="wide")

# ----------------------------------------------------------------- settings
GREEN, CYAN, VIOLET, AMBER, PINK = "#27E27A", "#38BDF8", "#A78BFA", "#FBBF24", "#F472B6"
CARD_BG, CARD_BORDER = "rgba(25,55,130,.55)", "rgba(130,180,255,.28)"

SAMPLE_PATH = os.path.join("samples", "team_meeting.wav")
OUTPUTS_DIR = "outputs"
BACKENDS = {"Auto (AssemblyAI, fallback Whisper)": "auto", "AssemblyAI": "assemblyai", "Local Whisper": "whisper"}
STAGES = ["Transcribing audio", "Refining transcript", "Generating meeting record"]
STAGE_SHORT = ["Speech-to-text", "Refine transcript", "Minutes & tasks"]
STAGE_TEXT = [
    "Converting speech into a raw transcript",
    "Fixing technical terms without changing meaning",
    "Writing minutes, decisions and action items",
]
MODEL_CHOICES = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
DEFAULT_REFINER = os.getenv("REFINER_MODEL", "openai/gpt-oss-120b")
DEFAULT_MINUTES = os.getenv("MINUTES_MODEL", "openai/gpt-oss-120b")


def spark_svg(size=110):
    petals = []
    for i in range(12):
        colour = GREEN if i % 2 == 0 else CYAN
        petals.append(
            f'<line class="petal" x1="50" y1="24" x2="50" y2="7" stroke="{colour}" '
            f'transform="rotate({i * 30} 50 50)" style="animation-delay:{i * 0.1:.1f}s"/>'
        )
    return f'<svg class="spark" width="{size}" height="{size}" viewBox="0 0 100 100">{"".join(petals)}</svg>'


st.markdown(
    f"""
<style>
.stApp {{
  background:
    radial-gradient(900px 480px at 50% -8%, rgba(39,226,122,.20), transparent 60%),
    radial-gradient(700px 420px at 100% 100%, rgba(56,189,248,.16), transparent 60%),
    linear-gradient(160deg, #081235 0%, #0E2A6B 55%, #0A3A63 100%);
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.6rem; max-width: 1250px; }}
section[data-testid="stSidebar"] {{ background: rgba(8,18,53,.88); border-right: 1px solid {CARD_BORDER}; }}

/* ---------- home ---------- */
.home-title {{ text-align:center; margin: 3.2rem 0 .3rem 0; font-size: 2.6rem; font-weight: 800;
  background: linear-gradient(90deg, {GREEN}, {CYAN} 60%, {VIOLET}); -webkit-background-clip: text;
  background-clip: text; color: transparent; }}
.home-sub {{ text-align:center; color:#b9ccf5; margin-bottom: 1.6rem; font-size: 1.05rem; }}
.st-key-composer {{ background: linear-gradient(180deg, rgba(25,60,140,.75), rgba(14,36,96,.80));
  border: 1.5px solid rgba(39,226,122,.55); border-radius: 26px; padding: 14px 18px;
  box-shadow: 0 10px 40px rgba(0,0,0,.35), 0 0 34px rgba(39,226,122,.18); }}
.st-key-composer [data-testid="stFileUploaderDropzone"] {{ border: 2px dashed rgba(39,226,122,.6);
  border-radius: 18px; background: rgba(39,226,122,.06); padding: 26px; }}
.model-line {{ color:#b9ccf5; font-size:.85rem; padding-top:.55rem; text-align:right; }}
.model-line b {{ color:{GREEN}; }}
.chips {{ display:flex; gap:10px; flex-wrap:wrap; justify-content:center; margin-top: 22px; }}
.chip {{ padding:6px 16px; border-radius:999px; font-size:.85rem; font-weight:600; color:#071433; }}

/* ---------- processing ---------- */
.proc {{ text-align:center; margin: .4rem auto 3rem; max-width: 640px; padding: 34px 20px;
  background: {CARD_BG}; border:1px solid {CARD_BORDER}; border-radius: 26px;
  box-shadow: 0 0 40px rgba(39,226,122,.15); }}
.proc-title {{ font-size:1.35rem; font-weight:700; margin-top:10px; }}
.proc-sub {{ color:#b9ccf5; margin-top:4px; }}
.pills {{ display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin-top:22px; }}
.pill {{ padding:6px 16px; border-radius:999px; font-size:.85rem; border:1px solid {CARD_BORDER}; color:#8fa7d9; }}
.pill.active {{ color:#071433; background:{GREEN}; border-color:{GREEN}; font-weight:700; box-shadow:0 0 16px rgba(39,226,122,.6); }}
.pill.done {{ color:{GREEN}; border-color:{GREEN}; }}
.spark {{ animation: spin 7s linear infinite; filter: drop-shadow(0 0 10px rgba(39,226,122,.55)); }}
.petal {{ stroke-width: 6; stroke-linecap: round; animation: pulse 1.2s ease-in-out infinite; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
@keyframes pulse {{ 0%,100% {{ opacity:.25; stroke-width:4; }} 50% {{ opacity:1; stroke-width:8; }} }}

/* ---------- results ---------- */
.brand {{ font-size:1.6rem; font-weight:800; background: linear-gradient(90deg, {GREEN}, {CYAN});
  -webkit-background-clip:text; background-clip:text; color:transparent; }}
.card {{ background:{CARD_BG}; border:1px solid {CARD_BORDER}; border-left:5px solid {CYAN};
  border-radius:14px; padding:14px 18px; margin-bottom:10px; }}
.card.green {{ border-left-color:{GREEN}; }} .card.cyan {{ border-left-color:{CYAN}; }}
.card.violet {{ border-left-color:{VIOLET}; }} .card.amber {{ border-left-color:{AMBER}; }}
.card.pink {{ border-left-color:{PINK}; }}
.card .title {{ font-weight:600; font-size:1rem; margin-bottom:6px; }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem; margin-right:6px;
  border:1px solid {CYAN}; color:#9bdcff; }}
.badge.unspec {{ color:{AMBER}; border-color:{AMBER}; font-style:italic; }}
.badge.ok {{ color:{GREEN}; border-color:{GREEN}; }}
.badge.warn {{ color:{AMBER}; border-color:{AMBER}; }}
.badge.time {{ color:{VIOLET}; border-color:{VIOLET}; }}
.mcard {{ background:{CARD_BG}; border:1px solid {CARD_BORDER}; border-radius:16px; padding:14px 16px; }}
.mcard .l {{ font-size:.82rem; color:#b9ccf5; }}
.mcard .v {{ font-size:1.7rem; font-weight:800; }}
.tline {{ margin-bottom:10px; line-height:1.55; }}
.tline mark {{ background:{AMBER}; color:#000; border-radius:3px; padding:0 2px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{ border-radius:10px 10px 0 0; padding:8px 16px; }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
  color:#04210f !important; font-weight:700; border-radius:12px; border:none;
  background: linear-gradient(90deg, {GREEN}, #7CF5B0); }}
.stButton > button, .stDownloadButton > button {{ border-radius:12px; }}
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------- helpers
def esc(x):
    return html.escape(str(x))


def fmt_time(seconds):
    m, s = divmod(int(seconds or 0), 60)
    return f"{m:02d}:{s:02d}"


def friendly_error(e):
    if isinstance(e, AudioError):
        return str(e)
    msg = str(e)
    if "GROQ_API_KEY" in msg or "ASSEMBLYAI_API_KEY" in msg:
        return f"{msg}. Add it to your .env file and restart the app."
    if "busy or rate-limited" in msg or "RateLimit" in type(e).__name__:
        return "The language model is busy or rate-limited. Please wait a minute and try again."
    if isinstance(e, FileNotFoundError) and "ffmpeg" in msg.lower():
        return "ffmpeg is not installed or not on PATH. Install it and restart the app."
    return msg or type(e).__name__


def diff_html(raw, refined):
    a, b = raw.split(), refined.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(esc(" ".join(a[i1:i2])))
        else:
            if i2 > i1:
                out.append(f"<span style='background:rgba(244,63,94,.30);text-decoration:line-through;padding:0 3px;border-radius:3px'>{esc(' '.join(a[i1:i2]))}</span>")
            if j2 > j1:
                out.append(f"<span style='background:rgba(39,226,122,.30);padding:0 3px;border-radius:3px'>{esc(' '.join(b[j2:j2]))}</span>")
    return " ".join(out)


def mark(text, query):
    safe = esc(text)
    if not query:
        return safe
    return re.sub(f"({re.escape(esc(query))})", r"<mark>\1</mark>", safe, flags=re.I)


def badge(text, kind=""):
    return f"<span class='badge {kind}'>{esc(text)}</span>"


def owner_badge(label, value):
    if str(value).lower() == "unspecified":
        return badge(f"{label}: unspecified", "unspec")
    return badge(f"{label}: {value}")


def metric_card(label, value, colour, icon):
    return (f"<div class='mcard' style='border-top:4px solid {colour}'>"
            f"<div class='l'>{icon} {esc(label)}</div><div class='v' style='color:{colour}'>{esc(value)}</div></div>")


def progress_html(step, models):
    if step >= 3:
        title, sub = "All done", "Preparing your results..."
    else:
        title, sub = f"Step {step + 1} of 3 · {STAGE_SHORT[step]}", STAGE_TEXT[step]
        if step == 1:
            sub += f" ({models[0]})"
        if step == 2:
            sub += f" ({models[1]})"
    pills = "".join(
        f"<span class='pill {'done' if i < step else 'active' if i == step else ''}'>{'✓ ' if i < step else ''}{n}</span>"
        for i, n in enumerate(STAGE_SHORT)
    )
    return f"<div class='proc'><div class='proc-title'>{title}</div><div class='proc-sub'>{esc(sub)}</div><div class='pills'>{pills}</div></div>"


MASCOT_LINES = [
    "Listening to your meeting & converting speech to text...",
    "Fixing technical terms cleanly without altering names or negations...",
    "Extracting meeting minutes, decisions, and action items...",
    "All done! Getting your results ready...",
]


def render_progress(slot, step, models):
    with slot.container():
        show_mascot("done" if step >= 3 else "working", MASCOT_LINES[min(step, 3)], height=210)
        st.markdown(progress_html(step, models), unsafe_allow_html=True)


def zip_from_dir(out_dir):
    buf = io.BytesIO()
    names = ["raw_transcript.txt", "refined_transcript.txt", "meeting_record.json", "meeting_record.md"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            p = os.path.join(out_dir, n)
            if os.path.exists(p):
                z.write(p, n)
    return buf.getvalue()


def save_run_data(result, out_dir):
    keep = {k: result[k] for k in (
        "stt_backend", "refiner_model", "minutes_model", "raw_transcript",
        "refined_transcript", "segments", "flags", "record", "name", "seconds")}
    with open(os.path.join(out_dir, "run_data.json"), "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False)


def list_runs():
    if not os.path.isdir(OUTPUTS_DIR):
        return []
    runs = []
    for d in os.listdir(OUTPUTS_DIR):
        p = os.path.join(OUTPUTS_DIR, d, "run_data.json")
        if os.path.exists(p):
            runs.append((os.path.getmtime(p), d))
    return [d for _, d in sorted(runs, reverse=True)]


def load_run(folder):
    out_dir = os.path.join(OUTPUTS_DIR, folder)
    with open(os.path.join(out_dir, "run_data.json"), encoding="utf-8") as f:
        result = json.load(f)
    result["out_dir"] = out_dir
    result["zip"] = zip_from_dir(out_dir)
    return result


def model_select(label, key, default):
    options = MODEL_CHOICES if default in MODEL_CHOICES else [default] + MODEL_CHOICES
    kwargs = dict(index=options.index(default), key=key)
    try:
        return st.selectbox(label, options, accept_new_options=True, **kwargs)
    except TypeError:
        return st.selectbox(label, options, **kwargs)


def run_pipeline_ui(path, display_name, glossary, backend, refiner_model, minutes_model, slot):
    st.session_state.pop("result", None)
    st.session_state.pop("error", None)
    start = time.time()
    models = (refiner_model, minutes_model)
    render_progress(slot, 0, models)

    def on_status(msg):
        if msg in STAGES:
            render_progress(slot, STAGES.index(msg), models)
        elif msg == "Done":
            render_progress(slot, 3, models)

    kwargs = dict(glossary=glossary, backend=backend, on_status=on_status)
    accepted = inspect.signature(process_audio).parameters
    if "refiner_model" in accepted:
        kwargs.update(refiner_model=refiner_model, minutes_model=minutes_model)
    try:
        result = process_audio(path, **kwargs)
        out_dir = os.path.join(OUTPUTS_DIR, os.path.splitext(display_name)[0])
        save_outputs(result, out_dir)
        result["name"] = display_name
        result["out_dir"] = out_dir
        result["seconds"] = time.time() - start
        save_run_data(result, out_dir)
        result["zip"] = zip_from_dir(out_dir)
        st.session_state["result"] = result
        st.session_state["celebrate"] = True
    except Exception as e:
        st.session_state["error"] = friendly_error(e)
    slot.empty()


# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("<div class='brand'>🔝 TalkToTasks</div>", unsafe_allow_html=True)
    st.caption("Audio → transcript → refined transcript → minutes, decisions & tasks")
    if not os.getenv("GROQ_API_KEY"):
        st.error("GROQ_API_KEY missing in .env, the language models cannot run.")
    if not os.getenv("ASSEMBLYAI_API_KEY"):
        st.info("No ASSEMBLYAI_API_KEY found, local Whisper will be used.")

    runs = list_runs()
    with st.expander(f"🕒 Recent Meetings ({len(runs)})", expanded=bool(runs)):
        if runs:
            pick = st.selectbox("Past run", runs, label_visibility="collapsed")
            if st.button("Open this run", width="stretch"):
                st.session_state["result"] = load_run(pick)
                st.session_state.pop("celebrate", None)
                st.session_state.pop("error", None)
                st.session_state.pop("audio_bytes", None)
                st.rerun()
        else:
            st.caption("Runs you process will appear here.")
    with st.expander("How it works"):
        st.markdown(
            "1. **Speech-to-text - ** makes the raw transcript.\n"
            "2. **Refiner - ** fixes technical terms; unsafe edits to names, numbers or negations are blocked.\n"
            "3. **Minutes - ** writes summary, decisions and action items.\n"
            "4. **Verifier - ** checks every quote and number against the transcript."
        )

# ----------------------------------------------------------------- home (composer)
result = st.session_state.get("result")
proc_slot = st.empty()

if not result:
    home = st.empty()
    with home.container():
        st.markdown("<div class='home-title'>TalkToTasks</div>", unsafe_allow_html=True)
        st.markdown("<div class='home-sub'>Drop a meeting recording and get a transcript, minutes, decisions and action items.</div>", unsafe_allow_html=True)
        if "error" in st.session_state:
            show_mascot("error", f"Oops, I could not process that recording.\n\nError: {st.session_state['error']}\n\nPlease check your settings and try again.", height=210)
            st.error(f"**Could not process this recording.** {st.session_state['error']}")
        else:
            show_mascot("idle", height=210)

        _, mid, _ = st.columns([1, 5, 1])
        with mid:
            with st.container(border=True, key="composer"):
                uploaded = st.file_uploader(
                    "Upload meeting recording",
                    type=sorted(e.lstrip(".") for e in SUPPORTED),
                    label_visibility="collapsed",
                    help="English-language audio. Supported: " + ", ".join(sorted(SUPPORTED)),
                )
                b1, b2, b3, b4 = st.columns([1.5, 1.4, 2.6, 1.4], vertical_alignment="center")
                with b1.popover("＋ Glossary", width="stretch"):
                    topic = st.text_input(
                        "Meeting topic / glossary (optional)",
                        placeholder="Kubernetes, PyTorch, CI pipeline",
                        help="Comma-separated domain terms. Helps the speech model and the refiner.",
                        key="glossary",
                    )
                with b2.popover("⚙️ Models", width="stretch"):
                    backend_label = st.selectbox("Speech-to-text", list(BACKENDS), key="stt_backend")
                    refiner_model = model_select("Refiner model", "refiner_model", DEFAULT_REFINER)
                    minutes_model = model_select("Minutes model", "minutes_model", DEFAULT_MINUTES)
                b3.markdown(
                    f"<div class='model-line'>Refiner <b>{esc(refiner_model.split('/')[-1])}</b> · "
                    f"Minutes <b>{esc(minutes_model.split('/')[-1])}</b></div>",
                    unsafe_allow_html=True,
                )
                go = b4.button("Process  ➜", type="primary", width="stretch", disabled=uploaded is None)
            _, sc, _ = st.columns([1, 2, 1])
            sample = sc.button("✨ Or try the sample meeting", width="stretch", disabled=not os.path.exists(SAMPLE_PATH))
        st.markdown(
            f"<div class='chips'>"
            f"<span class='chip' style='background:{GREEN}'>1 · Speech-to-text</span>"
            f"<span class='chip' style='background:{CYAN}'>2 · Refiner</span>"
            f"<span class='chip' style='background:{VIOLET}'>3 · Minutes</span>"
            f"<span class='chip' style='background:{AMBER}'>4 · Verifier</span></div>",
            unsafe_allow_html=True,
        )

    if go or sample:
        glossary = [t.strip() for t in topic.split(",") if t.strip()] or None
        backend = BACKENDS[backend_label]
        home.empty()
        if go:
            ext = os.path.splitext(uploaded.name)[1].lower()
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(uploaded.getvalue())
            st.session_state["audio_bytes"] = uploaded.getvalue()
            try:
                run_pipeline_ui(tmp.name, uploaded.name, glossary, backend, refiner_model, minutes_model, proc_slot)
            finally:
                os.unlink(tmp.name)
        else:
            with open(SAMPLE_PATH, "rb") as f:
                st.session_state["audio_bytes"] = f.read()
            run_pipeline_ui(SAMPLE_PATH, os.path.basename(SAMPLE_PATH), glossary, backend, refiner_model, minutes_model, proc_slot)
        st.rerun()
    st.stop()

# ----------------------------------------------------------------- results
record = result["record"]
segments = result["segments"]
speakers = sorted({s["speaker"] for s in segments if s.get("speaker")})
duration = max((s.get("end") or 0) for s in segments)
edits = sum(1 for s in segments if s.get("changed"))

h1, h2 = st.columns([5, 1.3], vertical_alignment="center")
h1.markdown(f"<div class='brand'>🔝 TalkToTasks</div><div style='color:#b9ccf5'>Results for <b>{esc(result['name'])}</b></div>", unsafe_allow_html=True)
if h2.button("＋ New recording", type="primary", width="stretch"):
    st.session_state.pop("result", None)
    st.session_state.pop("celebrate", None)
    st.session_state.pop("error", None)
    st.rerun()

cards = [
    ("Duration", fmt_time(duration), CYAN, "⏱️"),
    ("Speakers", len(speakers) or "n/a", VIOLET, "🗣️"),
    ("Decisions", len(record["decisions"]), GREEN, "✅"),
    ("Action items", len(record["action_items"]), AMBER, "📌"),
    ("Refiner edits", f"{edits} / {edits + len(result['flags'])}", PINK, "✏️"),
]
for col, args in zip(st.columns(5), cards):
    col.markdown(metric_card(*args), unsafe_allow_html=True)

if st.session_state.get("audio_bytes"):
    st.audio(st.session_state["audio_bytes"])

tab_over, tab_tr, tab_min, tab_act, tab_dl = st.tabs(
    ["📋 Overview", "📝 Transcripts", "🗂️ Minutes", "✅ Decisions & Actions", "⬇️ Downloads & About"]
)

# --- Overview Tab
with tab_over:
    show_mascot(
        "done",
        f"Meeting summarized!🥳 Found {len(record['decisions'])} decision & {len(record['action_items'])} action item.\n\n"
        "Overview: Check out the executive summary, key decisions, and main action items below.",
        height=190,
    )
    st.markdown("#### Summary")
    st.markdown(f"<div class='card pink'>{esc(record['summary'])}</div>", unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown("#### Key decisions")
        if record["decisions"]:
            for d in record["decisions"]:
                st.markdown(
                    f"<div class='card green'><div class='title'>{esc(d['decision'])}</div>"
                    f"{badge(d.get('timestamp') or '--:--', 'time')}"
                    f"{badge('verified', 'ok') if d.get('verified') else badge('check evidence', 'warn')}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No decisions were recorded in this meeting.")
    with right:
        st.markdown("#### Action items")
        if record["action_items"]:
            for a in record["action_items"]:
                st.markdown(
                    f"<div class='card amber'><div class='title'>{esc(a['task'])}</div>"
                    f"{owner_badge('Owner', a['owner'])}{owner_badge('Deadline', a['deadline'])}"
                    f"{badge(a.get('timestamp') or '--:--', 'time')}"
                    f"{badge('verified', 'ok') if a.get('verified') else badge('check evidence', 'warn')}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No action items were recorded in this meeting.")

# --- Transcripts Tab
with tab_tr:
    show_mascot(
        "done",
        "Transcripts View:\n\n"
        "Compare raw speech-to-text against refined text side-by-side. "
        "Filter by speaker, search key terms, or toggle edit highlights!",
        height=190,
    )
    f1, f2, f3, f4 = st.columns([2, 2, 1.3, 1.3])
    query = f1.text_input("Search transcript", placeholder="🔍 type a word...", label_visibility="collapsed")
    chosen = f2.multiselect("Speakers", speakers, placeholder="All speakers", label_visibility="collapsed") if speakers else []
    only_changed = f3.toggle("Changed lines only", value=False)
    show_diff = f4.toggle("Show edits", value=True, help="Green = added by refiner, red strikethrough = removed")

    col_a, col_b = st.columns(2)
    col_a.markdown("#### Raw transcript")
    col_b.markdown("#### Refined transcript")
    shown = 0
    for s in segments:
        if only_changed and not s.get("changed"):
            continue
        if chosen and s.get("speaker") not in chosen:
            continue
        if query and query.lower() not in (s["raw_text"] + " " + s["text"]).lower():
            continue
        shown += 1
        who = f"{s['speaker']}: " if s.get("speaker") else ""
        prefix = f"<b style='color:{CYAN}'>[{fmt_time(s.get('start'))}] {esc(who)}</b>"
        if show_diff and s.get("changed") and not query:
            ref_side = diff_html(s["raw_text"], s["text"])
        else:
            ref_side = mark(s["text"], query)
        col_a.markdown(f"<div class='tline'>{prefix}{mark(s['raw_text'], query)}</div>", unsafe_allow_html=True)
        col_b.markdown(f"<div class='tline'>{prefix}{ref_side}</div>", unsafe_allow_html=True)
    if shown == 0:
        st.caption("No lines match the current filters.")
    if query:
        st.caption("Edit highlighting is paused while searching.")
    if result["flags"]:
        with st.expander(f"🛡️ Refiner blocked {len(result['flags'])} edit(s) to protect meaning"):
            st.json(result["flags"])

# --- Minutes Tab
with tab_min:
    show_mascot(
        "done",
        "Topic Minutes:\n\n"
        "Here is the topic-by-topic breakdown of everything discussed during your meeting.",
        height=170,
    )
    if record["minutes"]:
        colours = ["violet", "cyan", "green", "amber", "pink"]
        for i, m in enumerate(record["minutes"], 1):
            st.markdown(
                f"<div class='card {colours[(i - 1) % 5]}'><div class='title'>{i}. {esc(m['topic'])}</div>{esc(m['discussion'])}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No minutes were generated.")


def unspecified_style(val):
    return f"color:{AMBER};font-style:italic" if str(val).lower() == "unspecified" else ""


# --- Decisions & Actions Tab
with tab_act:
    show_mascot(
        "done",
        "Decisions & Action Items:\n\n"
        "Every item is verified against exact timestamps and evidence quotes. "
        "Notice 'unspecified' tags in amber whenever details weren't explicitly stated in the recording.",
        height=190,
    )
    st.markdown("#### Key decisions")
    if record["decisions"]:
        df = pd.DataFrame(
            [{"Decision": d["decision"], "Time": d.get("timestamp", ""), "Verified": "💋" if d.get("verified") else "⚠️"} for d in record["decisions"]]
        )
        st.dataframe(df, width="stretch", hide_index=True)
        for d in record["decisions"]:
            with st.expander(f"Evidence: {d['decision'][:70]}"):
                st.write(f"“{d.get('evidence', '')}”  (at {d.get('timestamp', '?')})")
    else:
        st.caption("No decisions were recorded.")

    st.markdown("#### Action items")
    if record["action_items"]:
        df = pd.DataFrame(
            [{"Task": a["task"], "Owner": a["owner"], "Deadline": a["deadline"], "Time": a.get("timestamp", ""), "Verified": "💋" if a.get("verified") else "⚠️"} for a in record["action_items"]]
        )
        st.dataframe(df.style.map(unspecified_style, subset=["Owner", "Deadline"]), width="stretch", hide_index=True)
        st.caption("Amber 'unspecified' means it was not stated in the recording, nothing was guessed.")
        for a in record["action_items"]:
            with st.expander(f"Evidence: {a['task'][:70]}"):
                st.write(f"“{a.get('evidence', '')}”  (at {a.get('timestamp', '?')})")
    else:
        st.caption("No action items were recorded.")

    notes = record.get("verification_notes", [])
    with st.expander(f"🔍 Verification notes ({len(notes)})"):
        if notes:
            for n in notes:
                st.write("- " + n)
        else:
            st.write("All quotes and numbers were found in the transcript.")

# --- Downloads & About Tab
with tab_dl:
    show_mascot(
        "done",
        "⬇Export & Downloads:\n\n"
        "Download meeting deliverables in Markdown (.md), JSON, raw text, or a complete ZIP package.",
        height=170,
    )
    st.markdown("#### Download outputs")
    stem = os.path.splitext(result["name"])[0]
    d = st.columns(5)
    d[0].download_button("Raw transcript (.txt)", result["raw_transcript"], f"{stem}_raw_transcript.txt", width="stretch")
    d[1].download_button("Refined transcript (.txt)", result["refined_transcript"], f"{stem}_refined_transcript.txt", width="stretch")
    d[2].download_button("Meeting record (.md)", to_markdown(record), f"{stem}_meeting_record.md", width="stretch")
    d[3].download_button("Meeting record (.json)", json.dumps(record, indent=2, ensure_ascii=False), f"{stem}_meeting_record.json", mime="application/json", width="stretch")
    d[4].download_button("Everything (.zip)", result["zip"], f"{stem}_outputs.zip", mime="application/zip", type="primary", width="stretch")
    st.caption(f"Files are also saved on disk in `{result['out_dir']}/`.")

    with st.expander("Preview: Markdown"):
        st.code(to_markdown(record), language="markdown")
    with st.expander("Preview: JSON"):
        st.code(json.dumps(record, indent=2, ensure_ascii=False), language="json")