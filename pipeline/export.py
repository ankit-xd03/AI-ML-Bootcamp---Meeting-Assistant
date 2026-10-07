import json
import os


def to_markdown(record):
    out = ["# Meeting Record", "", "## Summary", record["summary"], "", "## Minutes"]
    for m in record["minutes"]:
        out += [f"### {m['topic']}", m["discussion"], ""]
    out.append("## Key Decisions")
    if record["decisions"]:
        for d in record["decisions"]:
            ts = f" ({d['timestamp']})" if d.get("timestamp") else ""
            out.append(f"- {d['decision']}{ts}")
    else:
        out.append("- None recorded")
    out += ["", "## Action Items"]
    if record["action_items"]:
        for a in record["action_items"]:
            ts = f" ({a['timestamp']})" if a.get("timestamp") else ""
            out.append(f"- {a['task']} | Owner: {a['owner']} | Deadline: {a['deadline']}{ts}")
    else:
        out.append("- None recorded")
    if record.get("verification_notes"):
        out += ["", "## Verification Notes"]
        out += [f"- {n}" for n in record["verification_notes"]]
    return "\n".join(out) + "\n"


def save_outputs(result, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "raw": os.path.join(out_dir, "raw_transcript.txt"),
        "refined": os.path.join(out_dir, "refined_transcript.txt"),
        "json": os.path.join(out_dir, "meeting_record.json"),
        "markdown": os.path.join(out_dir, "meeting_record.md"),
    }
    with open(paths["raw"], "w") as f:
        f.write(result["raw_transcript"])
    with open(paths["refined"], "w") as f:
        f.write(result["refined_transcript"])
    with open(paths["json"], "w") as f:
        json.dump(result["record"], f, indent=2, ensure_ascii=False)
    with open(paths["markdown"], "w") as f:
        f.write(to_markdown(result["record"]))
    return paths
