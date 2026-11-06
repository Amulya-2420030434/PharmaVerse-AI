import argparse, json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.scripts.train_model import train

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("metrics", type=Path)
    args = parser.parse_args()
    print(json.dumps(train(args.input, args.artifact, args.metrics), indent=2))
