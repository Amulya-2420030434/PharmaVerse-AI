"""Compatibility entry point for explicit TRACE-X downloads."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.scripts.download_trace_x import download

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--md5")
    args = parser.parse_args()
    download(args.url, args.output, expected_md5=args.md5)
