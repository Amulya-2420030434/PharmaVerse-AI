import argparse
import json
from collections import Counter
from pathlib import Path


def inspect(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = Counter(row.get("label") for row in rows)
    return {"path": str(path), "rows": len(rows), "fields": sorted({key for row in rows for key in row}), "labels": {str(key): value for key, value in counts.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    print(json.dumps(inspect(parser.parse_args().input), indent=2))
