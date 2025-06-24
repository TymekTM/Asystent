import json
import os
from collections import defaultdict
from datetime import datetime

USAGE_FILE = os.path.join("user_data", "usage_stats.jsonl")

os.makedirs("user_data", exist_ok=True)


def record_usage(module: str = "core", tokens: int = 0) -> None:
    """Record a usage event with module name and token count."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "module": module,
        "tokens": tokens,
    }
    try:
        with open(USAGE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logging.error("Failed to record usage entry: %s", e, exc_info=True)


def aggregate_usage() -> dict:
    """Aggregate usage data per day."""
    daily = defaultdict(
        lambda: {"requests": 0, "tokens": 0, "modules": defaultdict(int)}
    )
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = entry.get("timestamp")
                if not ts:
                    continue
                day = ts.split("T")[0]
                daily[day]["requests"] += 1
                daily[day]["tokens"] += int(entry.get("tokens", 0))
                mod = entry.get("module", "core")
                daily[day]["modules"][mod] += 1
    result = {}
    for day, stats in daily.items():
        result[day] = {
            "requests": stats["requests"],
            "tokens": stats["tokens"],
            "modules": dict(stats["modules"]),
        }
    return result
