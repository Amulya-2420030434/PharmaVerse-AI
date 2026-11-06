"""Download a bounded openFDA export explicitly requested by the operator."""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen


def download(url: str, output: Path, timeout: float = 30) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=timeout) as response:
        output.write_bytes(response.read())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://api.fda.gov/drug/ndc.json?limit=100")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    download(args.url, args.output)
