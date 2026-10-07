import json
import sys
from pipeline.minutes import generate_minutes

if len(sys.argv) > 1:
    text = open(sys.argv[1]).read()
else:
    text = (
        "Okay team, let's start with the API latency. Rahul said the p95 is around 300 milliseconds. "
        "Priya suggested maybe we should move to Redis caching, but we haven't decided yet. "
        "Let's go with the current database schema, we will not change it this sprint. "
        "Rahul will deploy the new CI pipeline by Friday. "
        "Someone needs to update the documentation. "
        "Also we should probably think about a load test at some point. "
        "Okay, that's all for today."
    )

result = generate_minutes(text)
print("MODEL:", result["model"])
print(json.dumps(result["record"], indent=2, ensure_ascii=False))
