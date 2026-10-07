import sys
from pipeline.refine import refine_segments, text_to_segments

SAMPLE = [
    "Okay team, let's fix the A P I latency, it should stay under 200 millliseconds.",
    "Rahul will deploy the new see eye pipeline by Friday.",
    "We will not move to cube flow this sprint.",
    "Priya sai,d the pie torch model needs 3 more days of trainingz.",
    "Nobody will touch the Kub.ernetes patch until Friday.",
]


def load_segments():
    if len(sys.argv) < 2:
        return [
            {"start": float(i * 5), "end": float(i * 5 + 5), "speaker": None, "text": t}
            for i, t in enumerate(SAMPLE)
        ]
    path = sys.argv[1]
    if path.endswith(".txt"):
        return text_to_segments(open(path).read())
    from pipeline.stt import transcribe
    return transcribe(path)["segments"]


result = refine_segments(load_segments())
print("MODEL:", result["model"])
for i, s in enumerate(result["segments"], 1):
    print(f"\n[{i}] {'CHANGED' if s['changed'] else 'same'}")
    print("  raw    :", s["raw_text"])
    print("  refined:", s["text"])
print("\nFLAGS:", result["flags"])
