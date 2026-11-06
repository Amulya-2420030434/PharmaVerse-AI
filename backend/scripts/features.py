import argparse
import json
from pathlib import Path
try:
    from app.ml.model import FEATURE_NAMES
except ModuleNotFoundError:
    from backend.app.ml.model import FEATURE_NAMES


def build(source: Path, destination: Path) -> int:
    count = 0
    with source.open(encoding="utf-8") as src, destination.open("w", encoding="utf-8") as dst:
        for line in src:
            row = json.loads(line)
            features = {name: float(row.get(name, 0)) for name in FEATURE_NAMES}
            features["label"] = row.get("label", 0)
            dst.write(json.dumps(features, sort_keys=True) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(build(args.input, args.output))
