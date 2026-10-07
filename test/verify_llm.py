import time
import difflib
from dotenv import load_dotenv
from groq import Groq
from pipeline.refine import signature, load_prompt

load_dotenv()
client = Groq()
SYSTEM = load_prompt(None)
MODELS = ["openai/gpt-oss-120b"]

CASES = [
    {
        "raw": "Rahul will not ship the Kub.ernetes paTch uNntil the Friday.",
        "expect": ["Kubernetes"],
        "keep": ["Rahul", "not", "Friday"],
    },
    {
        "raw": "Okay team, the A P I latency should stay under 200 milliseconds and Priya will deploy the see eye pipeline by Friday.",
        "expect": ["API", "CI pipeline"],
        "keep": ["200", "Priya", "Friday"],
    },
    {
        "raw": "We will not move to cube flow this sprint, and the pie torch model needs 3 more days.",
        "expect": ["Kubeflow", "PyTorch"],
        "keep": ["not", "3"],
    },
    {
        "raw": "If I was in place of you, I will have never did that.",
        "expect": [],
        "keep": ["never"],
    },
]


def run(model, raw):
    kwargs = {}
    if model.startswith("openai/gpt-oss"):
        kwargs["reasoning_effort"] = "low"
    start = time.time()
    r = client.chat.completions.create(
        model=model,
        temperature=0,
        max_completion_tokens=1500,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"[1] {raw}"}],
        **kwargs,
    )
    c = r.choices[0]
    return (c.message.content or "").strip().removeprefix("[1]").strip(), c.finish_reason, time.time() - start


def check(raw, out, case):
    problems = []
    if not out:
        return ["empty output"]
    if signature(out) != signature(raw):
        problems.append("numbers or negations changed")
    low = out.lower()
    for w in case["expect"]:
        if w.lower() not in low:
            problems.append(f"missing fix: {w}")
    for w in case["keep"]:
        if w.lower() not in low:
            problems.append(f"lost: {w}")
    ratio = difflib.SequenceMatcher(None, raw.lower(), low).ratio()
    if ratio < 0.7:
        problems.append(f"rewrote too much ({ratio:.2f})")
    return problems


for m in MODELS:
    print(f"\n=== {m} ===")
    passed = 0
    for i, case in enumerate(CASES, 1):
        try:
            out, finish, secs = run(m, case["raw"])
            problems = check(case["raw"], out, case)
        except Exception as e:
            print(f"case {i}: ERROR {type(e).__name__}: {e}")
            continue
        status = "PASS" if not problems else "FAIL"
        passed += not problems
        print(f"case {i}: {status} ({secs:.2f}s, finish={finish})")
        print("  out:", out)
        if problems:
            print("  problems:", "; ".join(problems))
    print(f"score: {passed}/{len(CASES)}")
