import polars as pl
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve, auc, f1_score
from sklearn.feature_selection import mutual_info_classif
from sklearn.model_selection import train_test_split
import os

OUT = "figures"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})
C_PK, C_KSA = "#2a9d8f", "#e76f51"

ev = pl.read_parquet("dataset_out/transactions.parquet")
ent = pl.read_parquet("dataset_out/entities.parquet")
med = pl.read_parquet("dataset_out/medicines.parquet")
bat = pl.read_parquet("dataset_out/batches.parquet")
print(f"Loaded {ev.height:,} transactions")

ft = ev.filter(pl.col("fraud_type").is_not_null()).group_by("fraud_type").len().sort("len", descending=True)
fig, ax = plt.subplots(figsize=(7,4))
ax.bar(ft["fraud_type"], ft["len"], color="#264653")
ax.set_title("Fig 1. Fraud Type Distribution")
ax.set_ylabel("Transactions"); plt.xticks(rotation=40, ha="right")
plt.tight_layout(); plt.savefig(f"{OUT}/fig1_fraud_types.png"); plt.close()

by_c = ev.group_by("country").agg([
    pl.col("is_fraud_ground_truth").mean().alias("gt"),
    pl.col("is_fraud_detected").mean().alias("det")
]).sort("country")
fig, ax = plt.subplots(figsize=(6,4))
x = np.arange(len(by_c)); w=0.35
ax.bar(x-w/2, by_c["gt"], w, label="Ground truth", color="#264653")
ax.bar(x+w/2, by_c["det"], w, label="Detected", color="#e9c46a")
ax.set_xticks(x); ax.set_xticklabels(by_c["country"])
ax.set_ylabel("Fraud rate"); ax.set_title("Fig 2. Fraud Rate by Jurisdiction (detection gap)")
ax.legend(); plt.tight_layout(); plt.savefig(f"{OUT}/fig2_fraud_by_country.png"); plt.close()

evj = ev.join(bat.select(["batch_id","medicine_id"]), on="batch_id", how="left") \
        .join(med.select(["medicine_id","is_cold_chain"]), on="medicine_id", how="left")
cold = evj.filter(pl.col("is_cold_chain"))["temperature"].drop_nulls().to_numpy()
amb  = evj.filter(~pl.col("is_cold_chain"))["temperature"].drop_nulls().to_numpy()
fig, ax = plt.subplots(figsize=(7,4))
ax.hist(cold, bins=60, alpha=0.7, label="Cold-chain (2-8C)", color=C_KSA, density=True)
ax.hist(amb, bins=60, alpha=0.7, label="Ambient (15-25C)", color=C_PK, density=True)
ax.axvspan(8, ax.get_xlim()[1], alpha=0.12, color="red", label="Excursion zone")
ax.set_xlabel("Temperature (C)"); ax.set_ylabel("Density")
ax.set_title("Fig 3. Temperature Distribution + Cold-Chain Excursion Zone")
ax.legend(); plt.tight_layout(); plt.savefig(f"{OUT}/fig3_temperature.png"); plt.close()

counts = ev.group_by("batch_id").len()["len"].to_numpy()
fig, ax = plt.subplots(figsize=(6,4))
vals, edges = np.histogram(counts, bins=40)
centers = (edges[:-1]+edges[1:])/2
ax.loglog(centers, vals+1, "o-", color="#264653", ms=4)
ax.set_xlabel("Events per batch (log)"); ax.set_ylabel("Frequency (log)")
ax.set_title("Fig 4. Batch Fan-out Distribution (heavy-tailed)")
plt.tight_layout(); plt.savefig(f"{OUT}/fig4_powerlaw.png"); plt.close()

tmp = ev.with_columns(pl.col("timestamp").str.slice(0,7).alias("month"))
mon = tmp.group_by("month").agg(pl.col("is_fraud_ground_truth").mean().alias("rate")).sort("month")
fig, ax = plt.subplots(figsize=(9,4))
ax.plot(mon["month"], mon["rate"], marker="o", color="#e76f51")
ax.axvspan(list(mon["month"]).index("2025-03") if "2025-03" in list(mon["month"]) else 0,
           list(mon["month"]).index("2025-05") if "2025-05" in list(mon["month"]) else 0,
           alpha=0.12, color="orange")
ax.set_title("Fig 5. Fraud Rate Over Time (temporal campaigns)")
ax.set_ylabel("Fraud rate"); plt.xticks(rotation=60, ha="right", fontsize=7)
plt.tight_layout(); plt.savefig(f"{OUT}/fig5_temporal.png"); plt.close()

feat = evj.join(bat.select(["batch_id","manufacturer_id"]), on="batch_id", how="left") \
          .join(ent.select(["entity_id","audit_score","gmp_compliant","years_of_operation",
                            "license_status"]).rename({"entity_id":"manufacturer_id"}),
                on="manufacturer_id", how="left")
X = feat.select([
    pl.col("temperature").fill_null(-999),
    pl.col("humidity").fill_null(-999),
    pl.col("qr_verified").cast(pl.Int8),
    pl.col("rfid_scanned").cast(pl.Int8),
    pl.col("seal_intact").cast(pl.Int8),
    pl.col("weight").fill_null(-999),
    pl.col("door_open").cast(pl.Int8),
    pl.col("battery_level"),
    pl.col("gps_lat").is_null().cast(pl.Int8).alias("gps_missing"),
    pl.col("rolling_excursion_rate").fill_null(0),
    pl.col("batch_tx_index"),
    pl.col("audit_score").fill_null(-999),
    pl.col("gmp_compliant").cast(pl.Int8),
    pl.col("years_of_operation").fill_null(-999),
    pl.col("is_cold_chain").cast(pl.Int8),
]).to_numpy()
y = feat["is_fraud_detected"].cast(pl.Int8).to_numpy()
fnames = ["temperature","humidity","qr_verified","rfid_scanned","seal_intact","weight",
          "door_open","battery_level","gps_missing","rolling_excursion_rate",
          "batch_tx_index","audit_score","gmp_compliant","years_op","is_cold_chain"]

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)

fig, ax = plt.subplots(figsize=(6,5))
results = {}
for name, model, col in [("Logistic Reg", LogisticRegression(max_iter=200), "#2a9d8f"),
                         ("Decision Tree", DecisionTreeClassifier(max_depth=8), "#e76f51")]:
    model.fit(Xtr, ytr)
    prob = model.predict_proba(Xte)[:,1]
    fpr,tpr,_ = roc_curve(yte, prob); a = auc(fpr,tpr)
    f1 = f1_score(yte, model.predict(Xte))
    results[name] = (a, f1)
    ax.plot(fpr,tpr,label=f"{name} (AUC={a:.3f})", color=col, lw=2)
ax.plot([0,1],[0,1],"k--",alpha=0.4)
ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
ax.set_title("Fig 6. Baseline Model Difficulty (ROC)")
ax.legend(); plt.tight_layout(); plt.savefig(f"{OUT}/fig6_roc.png"); plt.close()

mi = mutual_info_classif(Xtr[:50000], ytr[:50000], random_state=0)
order = np.argsort(mi)
fig, ax = plt.subplots(figsize=(7,5))
ax.barh([fnames[i] for i in order], mi[order], color="#264653")
ax.set_xlabel("Mutual information with label")
ax.set_title("Fig 7. Feature Leakage Audit (no single dominant feature)")
plt.tight_layout(); plt.savefig(f"{OUT}/fig7_mutual_info.png"); plt.close()

comp = {
    "Clean genuine": ev.filter((~pl.col("is_fraud_ground_truth")) & (~pl.col("is_suspicious_genuine"))).height,
    "Suspicious genuine": ev.filter(pl.col("is_suspicious_genuine")).height,
    "Obvious fraud": ev.filter(pl.col("is_fraud_ground_truth") & (~pl.col("is_masked"))).height,
    "Masked fraud": ev.filter(pl.col("is_masked")).height,
}
fig, ax = plt.subplots(figsize=(6,4))
ax.bar(comp.keys(), comp.values(), color=["#2a9d8f","#e9c46a","#f4a261","#e76f51"])
ax.set_yscale("log"); ax.set_ylabel("Transactions (log)")
ax.set_title("Fig 8. Dataset Composition (hard cases present)")
plt.xticks(rotation=25, ha="right")
plt.tight_layout(); plt.savefig(f"{OUT}/fig8_composition.png"); plt.close()

print("\n===== VALIDATION SUMMARY =====")
print(f"Total transactions      : {ev.height:,}")
print(f"Unique batches          : {ev['batch_id'].n_unique():,}")
print(f"Ground-truth fraud rate : {ev['is_fraud_ground_truth'].mean():.4f}")
print(f"Detected fraud rate     : {ev['is_fraud_detected'].mean():.4f}")
print(f"Suspicious genuine      : {comp['Suspicious genuine']:,}")
print(f"Masked fraud            : {comp['Masked fraud']:,}")
print(f"GPS-missing (MNAR)      : {ev.filter(pl.col('gps_lat').is_null()).height:,}")
print("\nBaseline difficulty (want AUC < ~0.90 = non-trivial):")
for k,(a,f1) in results.items():
    print(f"  {k:16s} AUC={a:.3f}  F1={f1:.3f}")
print(f"\nTop leakage feature MI   : {fnames[order[-1]]} = {mi[order[-1]]:.4f}")
print("(No single feature should perfectly predict the label.)")
print(f"\nFigures written to {OUT}/")
