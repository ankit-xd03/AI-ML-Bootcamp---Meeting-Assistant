import difflib
import re

from pipeline.refine import clean, signature

UNSPEC = "unspecified"


def norm(text):
    return re.sub(r"[^a-z0-9' ]+", " ", clean(text).lower()).split()


def evidence_found(evidence, full, lines):
    ev = " ".join(norm(evidence))
    if not ev:
        return False
    if ev in full:
        return True
    return any(difflib.SequenceMatcher(None, ev, line).ratio() >= 0.8 for line in lines)


def verify_record(record, segments):
    lines = [" ".join(norm(s["text"])) for s in segments]
    full = " ".join(lines)
    vocab = set(full.split())
    full_numbers = set(signature(" ".join(s["text"] for s in segments))[0])
    notes = []

    def check(kind, idx, item, text):
        ok = True
        if not evidence_found(item.get("evidence", ""), full, lines):
            notes.append(f"{kind} {idx}: evidence quote not found in transcript")
            ok = False
        if not set(signature(text)[0]) <= full_numbers:
            notes.append(f"{kind} {idx}: contains a number not found in transcript")
            ok = False
        item["verified"] = ok

    for i, d in enumerate(record["decisions"], 1):
        check("decision", i, d, d["decision"])

    for i, a in enumerate(record["action_items"], 1):
        owner = a["owner"].strip()
        if owner.lower() != UNSPEC:
            if re.fullmatch(r"(?i)(speaker\s*)?[a-z]", owner) or not set(norm(owner)) <= vocab:
                notes.append(f"action {i}: owner '{owner}' not found in transcript, reset to unspecified")
                a["owner"] = UNSPEC
        deadline = a["deadline"].strip()
        if deadline.lower() != UNSPEC and not set(norm(deadline)) <= vocab:
            notes.append(f"action {i}: deadline '{deadline}' not found in transcript, reset to unspecified")
            a["deadline"] = UNSPEC
        check("action", i, a, a["task"] + " " + a["deadline"])

    record["verification_notes"] = notes
    return record
