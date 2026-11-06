import argparse
import json
from pathlib import Path


def normalize(source: Path, destination: Path) -> int:
    count = 0
    with source.open(encoding="utf-8") as src, destination.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            row = json.loads(line)
            normalized = {str(key).strip().lower(): value for key, value in row.items()}
            dst.write(json.dumps(normalized, sort_keys=True) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(normalize(args.input, args.output))
