import sys
from pipeline.stt import transcribe, AudioError

backend = sys.argv[2] if len(sys.argv) > 2 else "auto"
try:
    result = transcribe(sys.argv[1], backend=backend)
    print("BACKEND:", result["backend"])
    print("SEGMENTS:", len(result["segments"]))
    print(result["text"][:1500])
except AudioError as e:
    print("ERROR:", e)
