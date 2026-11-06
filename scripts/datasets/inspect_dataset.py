import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.scripts.inspect_dataset import inspect

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    print(inspect(Path(parser.parse_args().input)))
