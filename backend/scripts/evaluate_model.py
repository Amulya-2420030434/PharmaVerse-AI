import argparse
import json
from pathlib import Path


def evaluate(source: Path, artifact: Path) -> dict:
    import joblib
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    try:
        from app.ml.model import FEATURE_NAMES
    except ModuleNotFoundError:
        from backend.app.ml.model import FEATURE_NAMES
    bundle = joblib.load(artifact)
    model = bundle["model"] if isinstance(bundle, dict) else bundle
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    x = [[float(row.get(name, 0)) for name in FEATURE_NAMES] for row in rows]
    y = [int(row["label"]) for row in rows]
    predicted = model.predict(x)
    return {"accuracy": accuracy_score(y, predicted), "precision": precision_score(y, predicted, zero_division=0), "recall": recall_score(y, predicted, zero_division=0), "n_samples": len(y)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.input, args.artifact), indent=2))
