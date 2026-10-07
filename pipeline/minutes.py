import json
import os
import re
import time
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from pipeline.refine import TRANSIENT

load_dotenv()

MINUTES_MODEL = os.getenv("MINUTES_MODEL", "openai/gpt-oss-120b")
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "minutes.txt")

_client = None


class Topic(BaseModel):
    topic: str
    discussion: str


class Decision(BaseModel):
    decision: str
    evidence: str = ""
    timestamp: str = ""


class ActionItem(BaseModel):
    task: str
    owner: str = "unspecified"
    deadline: str = "unspecified"
    evidence: str = ""
    timestamp: str = ""


class MeetingRecord(BaseModel):
    summary: str
    minutes: List[Topic] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)


def get_client():
    global _client
    if _client is None:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = Groq(api_key=key)
    return _client


def parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    return json.loads(text)


def normalize(record):
    for a in record.action_items:
        if not a.owner.strip() or a.owner.strip().lower() in {"none", "n/a", "unknown", "null"}:
            a.owner = "unspecified"
        if not a.deadline.strip() or a.deadline.strip().lower() in {"none", "n/a", "unknown", "null"}:
            a.deadline = "unspecified"
    return record


def create_with_retry(**kwargs):
    waits = [5, 15, 30, 60]
    for attempt in range(len(waits) + 1):
        try:
            return get_client().chat.completions.create(**kwargs)
        except TRANSIENT:
            if attempt == len(waits):
                raise RuntimeError("The language model is busy or rate-limited. Please wait a minute and try again.")
            time.sleep(waits[attempt])


def generate_minutes(refined_text, model=MINUTES_MODEL):
    with open(PROMPT_PATH) as f:
        system = f.read()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Transcript:\n" + refined_text},
    ]
    extra = {"reasoning_effort": os.getenv("MINUTES_EFFORT", "medium")} if model.startswith("openai/gpt-oss") else {}
    last_error = None
    for attempt in range(2):
        r = create_with_retry(
            model=model,
            temperature=0,
            max_completion_tokens=6000,
            response_format={"type": "json_object"},
            messages=messages,
            **extra,
        )
        content = (r.choices[0].message.content or "").strip()
        content = content.replace("\u202f", " ").replace("\u00a0", " ")
        try:
            record = normalize(MeetingRecord(**parse_json(content)))
            return {"record": record.model_dump(), "model": model}
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            last_error = e
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": f"Your output was invalid ({e}). Return only the corrected JSON object."})
    raise RuntimeError(f"Could not produce a valid meeting record: {last_error}")
