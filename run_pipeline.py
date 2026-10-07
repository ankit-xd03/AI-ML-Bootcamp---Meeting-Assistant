import os
import sys

from pipeline.export import save_outputs
from pipeline.run import process_audio
from pipeline.stt import AudioError

path = sys.argv[1]
try:
    result = process_audio(path, on_status=lambda m: print(">>", m))
except AudioError as e:
    print("ERROR:", e)
    sys.exit(1)
except Exception as e:
    print("PROCESSING FAILED:", e)
    sys.exit(1)

out_dir = os.path.join("outputs", os.path.splitext(os.path.basename(path))[0])
paths = save_outputs(result, out_dir)
print("\nSTT:", result["stt_backend"], "| REFINER:", result["refiner_model"], "| MINUTES:", result["minutes_model"])
print("\n" + open(paths["markdown"]).read())
print("REFINER FLAGS:", result["flags"])
print("SAVED TO:", out_dir)
