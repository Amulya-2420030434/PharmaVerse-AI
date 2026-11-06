"""Train the research model from the downloaded TRACE-X transaction data."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit


FEATURES = ["anomaly_count", "high_severity_count", "identity_anomaly_count", "sensor_anomaly_count"]


def build_frame(path: Path) -> pd.DataFrame:
    columns = [
        "batch_id", "temperature", "humidity", "qr_verified", "rfid_scanned",
        "seal_intact", "is_fraud_ground_truth", "is_fraud_detected",
        "duplicate_serial", "rolling_excursion_rate", "cumulative_excursion_time",
    ]
    tx = pd.read_csv(path, usecols=columns)
    bools = ["qr_verified", "rfid_scanned", "seal_intact", "is_fraud_detected", "duplicate_serial"]
    for column in bools:
        tx[column] = tx[column].astype(str).str.lower().isin(["true", "1", "yes"])
    tx["temperature"] = pd.to_numeric(tx["temperature"], errors="coerce")
    tx["humidity"] = pd.to_numeric(tx["humidity"], errors="coerce")
    tx["rolling_excursion_rate"] = pd.to_numeric(tx["rolling_excursion_rate"], errors="coerce").fillna(0)
    tx["cumulative_excursion_time"] = pd.to_numeric(tx["cumulative_excursion_time"], errors="coerce").fillna(0)
    tx["sensor_anomaly"] = (
        tx["temperature"].isna() | tx["humidity"].isna() |
        (tx["rolling_excursion_rate"] > 0) | (tx["cumulative_excursion_time"] > 0)
    )
    tx["identity_anomaly"] = (~tx["qr_verified"]) | (~tx["rfid_scanned"]) | (~tx["seal_intact"]) | tx["duplicate_serial"]
    tx["high_severity"] = tx["identity_anomaly"] | (tx["rolling_excursion_rate"] > 0.5)
    grouped = tx.groupby("batch_id", sort=True)
    frame = grouped.agg(
        anomaly_count=("sensor_anomaly", "sum"),
        high_severity_count=("high_severity", "sum"),
        identity_anomaly_count=("identity_anomaly", "sum"),
        sensor_anomaly_count=("sensor_anomaly", "sum"),
        label=("is_fraud_ground_truth", "max"),
    ).reset_index()
    frame["label"] = frame["label"].astype(str).str.lower().isin(["true", "1", "yes"]).astype(int)
    return frame


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "data/raw/trace_x/Phase1_Dataset/dataset/transactions.csv"
    output = root / "data/models/pharmaverse_fraud_model.joblib"
    metadata_path = root / "data/models/model_metadata.json"
    metrics_path = root / "data/metrics/model_evaluation.json"
    confusion_path = root / "data/metrics/confusion_matrix.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    frame = build_frame(source)
    groups = frame["batch_id"]
    outer = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(outer.split(frame, frame["label"], groups))
    inner = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_pool = frame.iloc[train_idx]
    pool_train_idx, pool_val_idx = next(
        inner.split(train_pool, train_pool["label"], train_pool["batch_id"])
    )
    train = train_pool.iloc[pool_train_idx]
    val = train_pool.iloc[pool_val_idx]
    test = frame.iloc[test_idx]
    train_groups = set(train["batch_id"])
    validation_groups = set(val["batch_id"])
    test_groups = set(test["batch_id"])
    assert not train_groups & validation_groups
    assert not train_groups & test_groups
    assert not validation_groups & test_groups
    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "RandomForestClassifier": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    }
    results = {}
    for name, model in models.items():
        model.fit(train[FEATURES], train["label"])
        prediction = model.predict(test[FEATURES])
        probability = model.predict_proba(test[FEATURES])[:, 1]
        results[name] = {
            "accuracy": accuracy_score(test["label"], prediction),
            "precision": precision_score(test["label"], prediction, zero_division=0),
            "recall": recall_score(test["label"], prediction, zero_division=0),
            "f1": f1_score(test["label"], prediction, zero_division=0),
            "roc_auc": roc_auc_score(test["label"], probability),
            "pr_auc": average_precision_score(test["label"], probability),
        }
    selected = max(results, key=lambda name: (results[name]["f1"], results[name]["roc_auc"]))
    model = models[selected]
    model.fit(frame[FEATURES], frame["label"])
    payload = {"model": model, "metrics": results[selected], "feature_names": FEATURES, "model_name": selected}
    joblib.dump(payload, output)
    metrics_path.write_text(json.dumps({
        "feature_names": FEATURES,
        "group_counts": {
            "train": len(train_groups), "validation": len(validation_groups), "test": len(test_groups)
        },
        "class_distribution": {
            "all": frame["label"].value_counts().sort_index().to_dict(),
            "test": test["label"].value_counts().sort_index().to_dict(),
        },
        "dataset": "TRACE-X synthetic benchmark",
        "rows": len(frame), "fraud_rows": int(frame["label"].sum()),
        "train_rows": len(train), "validation_rows": len(val), "test_rows": len(test),
        "grouping": "batch_id", "random_seed": 42, "models": results,
        "selected_model": selected,
    }, indent=2))
    test_prediction = models[selected].fit(train[FEATURES], train["label"]).predict(test[FEATURES])
    confusion_path.write_text(json.dumps({
        "labels": [0, 1],
        "matrix": confusion_matrix(test["label"], test_prediction).tolist(),
        "model": selected,
    }, indent=2))
    metadata_path.write_text(json.dumps({
        "dataset": "TRACE-X synthetic benchmark",
        "source": str(source),
        "model": selected,
        "feature_names": FEATURES,
        "label": "is_fraud_ground_truth aggregated by batch_id",
        "random_seed": 42,
        "grouping": "batch_id",
        "fit_scope": "full aggregated dataset for runtime artifact; metrics use held-out grouped test split",
    }, indent=2))
    print(json.dumps({"artifact": str(output), "metrics": results, "selected_model": selected}, indent=2))


if __name__ == "__main__":
    main()
