"""Check a trials.jsonl for the three difficulty-4/5 questions.

Usage:
    python3 scripts/inspect_trials.py results/<timestamp>/trials.jsonl
"""

import json
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
    files = [path] if path.is_file() else sorted(path.glob("*/trials.jsonl"))
    if not files:
        raise SystemExit(f"no trials.jsonl under {path}")
    for file in files:
        print(f"\n== {file}")
        for line in file.read_text().splitlines():
            row = json.loads(line)
            report = row.get("subordinate_text") or ""
            print(f"\n[{row['condition']}] verified leader={row.get('leader_verified')} worker={row.get('worker_verified')}")
            print(f"  report mentions 150: {_has_150(report)}")
            print(f"  report refuses role: {_refuses(report)}")
            print("  REPORT:", " ".join(report.split()))
            for role in ("leader", "worker"):
                raw = (row["calls"][role].get("raw") or "")
                print(f"  {role} mentions R-150: {'R-150' in raw}  mentions 150: {_has_150(raw)}")
                print(f"  {role} RAW:", " ".join(raw.split()))


def _has_150(text: str) -> bool:
    return "150" in text


def _refuses(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in ("i can't help", "i cannot help", "i can’t help", "cannot assist", "i must refuse"))


if __name__ == "__main__":
    main()
