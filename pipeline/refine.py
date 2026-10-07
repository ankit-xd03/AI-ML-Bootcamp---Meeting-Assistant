import difflib
import os
import re
import time
from collections import Counter

import groq
from dotenv import load_dotenv

load_dotenv()

REFINER_MODEL = os.getenv("REFINER_MODEL", "openai/gpt-oss-120b")
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "refine.txt")
BATCH_SEGMENTS = 20
BATCH_WORDS = 500
MAX_SEGMENT_WORDS = 60

TRANSIENT = (
    groq.RateLimitError,
    groq.APIConnectionError,
    groq.APITimeoutError,
    groq.InternalServerError,
)

NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
    "billion", "first", "second", "third", "half", "double", "triple",
}
NEGATIONS = {
    "not", "no", "never", "none", "nobody", "nothing", "nowhere",
    "neither", "nor", "without", "cannot",
}
DIGITS = re.compile(r"\d+(?:[.,]\d+)*")
WORDS = re.compile(r"[a-z]+")
NEG_RE = re.compile(r"\b(?:" + "|".join(sorted(NEGATIONS)) + r")\b")
LINE = re.compile(r"^\[(\d+)\]\s*(.*)$")

_client = None


def clean(text):
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u202f", " ")
        .replace("\u00a0", " ")
    )


def get_client():
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = groq.Groq(api_key=key)
    return _client


def load_prompt(glossary=None):
    with open(PROMPT_PATH) as f:
        text = f.read()
    if glossary:
        text += "\nDomain terms that may appear in this meeting: " + ", ".join(glossary)
    return text


def call_llm(system, user, model, retries=4):
    extra = {"reasoning_effort": "low"} if model.startswith("openai/gpt-oss") else {}
    for attempt in range(retries):
        try:
            r = get_client().chat.completions.create(
                model=model,
                temperature=0,
                max_completion_tokens=4000,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **extra,
            )
            return (r.choices[0].message.content or "").strip()
        except TRANSIENT:
            if attempt == retries - 1:
                raise
            time.sleep(5 * 3 ** attempt)


def signature(text):
    low = clean(text).lower()
    low = re.sub(r"n't\b", " not", low)
    low = low.replace("cannot", "can not")
    nums = Counter(DIGITS.findall(low))
    nums.update(w for w in WORDS.findall(low) if w in NUMBER_WORDS)
    negs = Counter(NEG_RE.findall(low))
    return nums, negs


def tokens(text):
    out = []
    for raw in clean(text).split():
        norm = re.sub(r"[^\w']", "", raw.lower())
        if norm:
            out.append((norm, raw))
    return out


def is_protected(norm, orig, position, from_raw):
    if DIGITS.search(norm) or norm in NUMBER_WORDS or norm in NEGATIONS or norm.endswith("n't"):
        return True
    if from_raw and position > 0 and len(norm) >= 3 and orig[:1].isupper():
        return True
    return False


def edit_is_safe(raw, refined):
    a, b = tokens(raw), tokens(refined)
    matcher = difflib.SequenceMatcher(None, [t[0] for t in a], [t[0] for t in b], autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue
        for k in range(i1, i2):
            if is_protected(a[k][0], a[k][1], k, True):
                return False
        for k in range(j1, j2):
            if is_protected(b[k][0], b[k][1], k, False):
                return False
    return True


def too_different(raw, refined):
    if len(raw.split()) < 5:
        return False
    ratio = difflib.SequenceMatcher(None, clean(raw).lower(), clean(refined).lower()).ratio()
    return ratio < 0.6


def split_long(segments):
    out = []
    for seg in segments:
        if len(seg["text"].split()) <= MAX_SEGMENT_WORDS:
            out.append(dict(seg))
            continue
        current, count = [], 0
        for sentence in re.split(r"(?<=[.!?])\s+", seg["text"].strip()):
            n = len(sentence.split())
            if current and count + n > MAX_SEGMENT_WORDS:
                out.append(dict(seg, text=" ".join(current)))
                current, count = [], 0
            current.append(sentence)
            count += n
        if current:
            out.append(dict(seg, text=" ".join(current)))
    return out


def make_batches(segments):
    batches, current, words = [], [], 0
    for i, seg in enumerate(segments):
        n = len(seg["text"].split())
        if current and (len(current) >= BATCH_SEGMENTS or words + n > BATCH_WORDS):
            batches.append(current)
            current, words = [], 0
        current.append(i)
        words += n
    if current:
        batches.append(current)
    return batches


def parse_lines(text, expected_ids):
    found = {}
    for line in text.splitlines():
        m = LINE.match(line.strip())
        if m:
            found[int(m.group(1))] = m.group(2).strip()
    if set(found) != set(expected_ids):
        return None
    return found


def refine_batch(system, segments, ids, model):
    user = "\n".join(f"[{i + 1}] {segments[i]['text']}" for i in ids)
    expected = [i + 1 for i in ids]
    for _ in range(2):
        parsed = parse_lines(call_llm(system, user, model), expected)
        if parsed is not None:
            return parsed
    return None


def refine_segments(segments, glossary=None, model=REFINER_MODEL):
    segments = split_long(segments)
    if not segments:
        raise ValueError("No transcript segments to refine.")
    system = load_prompt(glossary)
    batches = make_batches(segments)
    refined = [dict(s, raw_text=s["text"], changed=False) for s in segments]
    flags, llm_errors = [], 0
    for b, ids in enumerate(batches, 1):
        try:
            parsed = refine_batch(system, segments, ids, model)
        except TRANSIENT as e:
            llm_errors += 1
            flags.append({"batch": b, "reason": f"LLM unavailable ({type(e).__name__}), kept original"})
            continue
        if parsed is None:
            flags.append({"batch": b, "reason": "model returned mismatched segment IDs, kept original"})
            continue
        for i in ids:
            raw = segments[i]["text"]
            out = clean(parsed[i + 1]).strip()
            if not out or out == raw:
                continue
            if signature(out) != signature(raw) or not edit_is_safe(raw, out):
                flags.append({"segment": i + 1, "reason": "edit touched a name, number or negation, kept original"})
                continue
            if too_different(raw, out):
                flags.append({"segment": i + 1, "reason": "rewrote too much, kept original"})
                continue
            refined[i]["text"] = out
            refined[i]["changed"] = True
    if llm_errors == len(batches):
        raise RuntimeError("Transcript refinement failed: the language model was unreachable for every batch.")
    return {
        "segments": refined,
        "raw_text": " ".join(s["raw_text"] for s in refined),
        "refined_text": " ".join(s["text"] for s in refined),
        "flags": flags,
        "model": model,
    }


def text_to_segments(text):
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [{"start": 0.0, "end": 0.0, "speaker": None, "text": s} for s in sentences if s]


def format_transcript(segments, use="text"):
    lines = []
    for s in segments:
        minutes, seconds = divmod(int(s.get("start") or 0), 60)
        who = f"{s['speaker']}: " if s.get("speaker") else ""
        lines.append(f"[{minutes:02d}:{seconds:02d}] {who}{s[use]}")
    return "\n".join(lines)
