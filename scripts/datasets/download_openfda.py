"""Compatibility entry point for the dataset acquisition workflow."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.scripts.download_openfda import download

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://api.fda.gov/drug/ndc.json?limit=100")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    download(args.url, args.output)
