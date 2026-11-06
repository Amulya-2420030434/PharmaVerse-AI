"""Train an optional artifact from JSONL features. Metrics are computed, never fabricated."""
import argparse
import json
from pathlib import Path


def train(source: Path, artifact: Path, metrics_path: Path) -> dict:
    import joblib
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    try:
        from app.ml.model import FEATURE_NAMES
    except ModuleNotFoundError:
        from backend.app.ml.model import FEATURE_NAMES
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    x = [[float(row.get(name, 0)) for name in FEATURE_NAMES] for row in rows]
    y = [int(row["label"]) for row in rows]
    if len(set(y)) < 2:
        raise ValueError("training requires both classes")
    model = LogisticRegression(random_state=42).fit(x, y)
    predictions = model.predict(x)
    metrics = {"accuracy": accuracy_score(y, predictions), "precision": precision_score(y, predictions, zero_division=0), "recall": recall_score(y, predictions, zero_division=0), "n_samples": len(y)}
    artifact.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "metrics": metrics}, artifact)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("metrics", type=Path)
    args = parser.parse_args()
    print(json.dumps(train(args.input, args.artifact, args.metrics), indent=2))
