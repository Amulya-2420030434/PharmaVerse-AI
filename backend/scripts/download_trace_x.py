"""Download and verify TRACE-X with resumable chunked HTTP reads."""
import argparse
import hashlib
from pathlib import Path
from time import sleep
from urllib.request import Request, urlopen


def download(
    url: str,
    output: Path,
    timeout: float = 60,
    expected_md5: str | None = None,
    retries: int = 4,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries):
        offset = output.stat().st_size if output.exists() else 0
        request = Request(url)
        if offset:
            request.add_header("Range", f"bytes={offset}-")
        try:
            with urlopen(request, timeout=timeout) as response:
                mode = "ab" if offset and response.status == 206 else "wb"
                with output.open(mode) as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
            if expected_md5:
                digest = hashlib.md5(output.read_bytes()).hexdigest()
                if digest != expected_md5:
                    raise RuntimeError(
                        f"MD5 mismatch: expected {expected_md5}, got {digest}"
                    )
            return
        except Exception:
            if attempt == retries - 1:
                raise
            sleep(2**attempt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="URL from the approved TRACE-X manifest")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--md5")
    args = parser.parse_args()
    download(args.url, args.output, expected_md5=args.md5)
