import argparse
import hashlib
import math
from datetime import datetime, timedelta

import numpy as np
import polars as pl
import yaml
import networkx as nx
from faker import Faker


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


HUB_COORDS = {
    "Riyadh": (24.71, 46.68), "Jeddah": (21.49, 39.19), "Dammam": (26.43, 50.10),
    "Mecca": (21.39, 39.86), "Medina": (24.52, 39.57),
    "Karachi": (24.86, 67.01), "Lahore": (31.55, 74.34), "Islamabad": (33.68, 73.05),
    "Faisalabad": (31.42, 73.08), "Peshawar": (34.02, 71.58), "Quetta": (30.18, 66.98),
}


def gen_entities(cfg, rng):
    rows = []
    date_start = datetime.fromisoformat(cfg["date_start"])
    for country, c in cfg["countries"].items():
        fake = Faker(c["faker_locale"])
        Faker.seed(cfg["seed"])
        for etype, count in c["entities"].items():
            for i in range(count):
                hub = rng.choice(c["hubs"])
                base_lat, base_lon = HUB_COORDS[hub]
                lat = base_lat + rng.normal(0, 0.15)
                lon = base_lon + rng.normal(0, 0.15)
                years = int(rng.integers(1, 30))
                audit = float(np.clip(rng.normal(78, 15), 0, 100))
                lic = rng.choice(["active", "expired", "suspended"], p=[0.90, 0.07, 0.03])
                gmp = bool(rng.random() > 0.10)
                rows.append({
                    "entity_id": f"{country}_{etype[:3].upper()}_{i:04d}",
                    "entity_type": etype,
                    "country": country,
                    "regulator": c["regulator"],
                    "enforcement_level": c["enforcement_level"],
                    "city": hub,
                    "latitude": round(lat, 5),
                    "longitude": round(lon, 5),
                    "license_number": f"{c['regulator']}-{rng.integers(10000,99999)}",
                    "license_status": lic,
                    "license_expiry": (date_start + timedelta(days=int(rng.integers(-200, 900)))).date().isoformat(),
                    "gmp_compliant": gmp,
                    "pics_compliant": bool(gmp and country == "PK" and rng.random() > 0.3),
                    "sfda_gmp_status": ("pass" if gmp else "pending") if country == "KSA" else None,
                    "audit_score": round(audit, 1),
                    "years_of_operation": years,
                    "is_importer": bool(rng.random() < 0.15),
                })
    return pl.DataFrame(rows)


def build_graph(entities, cfg, rng):
    G = nx.DiGraph()
    df = entities.to_pandas()
    for _, r in df.iterrows():
        G.add_node(r["entity_id"], **r.to_dict())

    def ids(etype, country=None):
        m = df["entity_type"] == etype
        if country:
            m &= df["country"] == country
        return df[m]

    dists = df[df["entity_type"] == "distributor"].copy()
    weights = rng.zipf(2.0, size=len(dists)).astype(float)
    dist_weight = dict(zip(dists["entity_id"], weights / weights.sum()))

    for _, ph in df[df["entity_type"] == "pharmacy"].iterrows():
        same = dists[dists["country"] == ph["country"]]
        d = same.assign(dist=[haversine(ph["latitude"], ph["longitude"], r["latitude"], r["longitude"])
                              for _, r in same.iterrows()])
        nearest = d.nsmallest(int(rng.integers(2, 4)), "dist")
        for _, dd in nearest.iterrows():
            G.add_edge(dd["entity_id"], ph["entity_id"], rel="dist_to_pharmacy")

    for country in cfg["countries"]:
        mans = ids("manufacturer", country)
        whs = ids("warehouse", country)
        dds = ids("distributor", country)
        for _, m in mans.iterrows():
            for _, w in whs.sample(min(3, len(whs)), random_state=int(rng.integers(1e6))).iterrows():
                G.add_edge(m["entity_id"], w["entity_id"], rel="man_to_warehouse")
        for _, w in whs.iterrows():
            for _, dd in dds.sample(min(5, len(dds)), random_state=int(rng.integers(1e6))).iterrows():
                G.add_edge(w["entity_id"], dd["entity_id"], rel="warehouse_to_dist")

    pk_man = ids("manufacturer", "PK")
    ksa_dist = ids("distributor", "KSA")
    n_cross = int(len(pk_man) * cfg["cross_border"]["edge_fraction"] * 5) + 1
    for _ in range(n_cross):
        m = pk_man.sample(1, random_state=int(rng.integers(1e6))).iloc[0]
        d = ksa_dist.sample(1, random_state=int(rng.integers(1e6))).iloc[0]
        G.add_edge(m["entity_id"], d["entity_id"], rel="cross_border", cross_border=True)

    return G, dist_weight


def gen_medicines(cfg, rng):
    types = list(cfg["storage_ranges"].keys())
    rows = []
    for i in range(cfg["n_medicines"]):
        dt = rng.choice(types)
        sr = cfg["storage_ranges"][dt]
        rows.append({
            "medicine_id": f"MED_{i:04d}",
            "drug_type": dt,
            "storage_min": sr["min"],
            "storage_max": sr["max"],
            "is_cold_chain": sr["cold_chain"],
            "shelf_life_days": int(rng.choice([180, 365, 540, 730])),
            "price": round(float(rng.lognormal(2.5, 0.8)), 2),
        })
    return pl.DataFrame(rows)


def gen_batches(cfg, entities, medicines, rng, n_batches):
    date_start = datetime.fromisoformat(cfg["date_start"])
    date_end = datetime.fromisoformat(cfg["date_end"])
    span = (date_end - date_start).days
    mans = entities.filter(pl.col("entity_type") == "manufacturer")
    man_ids = mans["entity_id"].to_list()
    man_country = dict(zip(mans["entity_id"], mans["country"]))
    med_ids = medicines["medicine_id"].to_list()
    med_shelf = dict(zip(medicines["medicine_id"], medicines["shelf_life_days"]))
    rows = []
    for i in range(n_batches):
        man = rng.choice(man_ids)
        med = rng.choice(med_ids)
        prod = date_start + timedelta(days=int(rng.integers(0, span - 200)))
        rows.append({
            "batch_id": f"BATCH_{i:06d}",
            "medicine_id": med,
            "manufacturer_id": man,
            "country_of_origin": man_country[man],
            "production_date": prod.date().isoformat(),
            "expiry_date": (prod + timedelta(days=med_shelf[med])).date().isoformat(),
            "quantity": int(rng.lognormal(8, 1)),
        })
    return pl.DataFrame(rows)


def assign_fraud(cfg, batches, entities, rng):
    ent = entities.to_pandas().set_index("entity_id")
    ftypes = list(cfg["fraud"]["type_distribution"].keys())
    fprobs = list(cfg["fraud"]["type_distribution"].values())
    campaigns = [(datetime.fromisoformat(c["window"][0]),
                  datetime.fromisoformat(c["window"][1]), c["boost"])
                 for c in cfg["temporal_campaigns"]]
    ring_entities = set()
    for r in cfg["fraud_rings"]:
        pool = entities.filter(
            (pl.col("country") == r["country"]) &
            (pl.col("entity_type").is_in(r["entity_types"]))
        )["entity_id"].to_list()
        ring_entities.update(rng.choice(pool, size=min(3, len(pool)), replace=False).tolist())

    target = cfg["fraud"]["base_rate"]
    rows = []
    for b in batches.iter_rows(named=True):
        man = b["manufacturer_id"]
        e = ent.loc[man]
        base = -2.4
        if e["license_status"] != "active":
            base += 0.8
        if not e["gmp_compliant"]:
            base += 0.7
        base += (70 - e["audit_score"]) / 40.0
        if man in ring_entities:
            base += 1.2
        prod = datetime.fromisoformat(b["production_date"])
        for cs, ce, boost in campaigns:
            if cs <= prod <= ce:
                base += math.log(boost)
        p = sigmoid(base + rng.normal(0, 0.5))
        is_fraud = rng.random() < p
        ftype = rng.choice(ftypes, p=fprobs) if is_fraud else None
        rows.append({"batch_id": b["batch_id"],
                     "is_fraud_ground_truth": bool(is_fraud),
                     "fraud_type": ftype,
                     "in_ring": man in ring_entities})
    fr = pl.DataFrame(rows, infer_schema_length=len(rows))
    rate = fr["is_fraud_ground_truth"].mean()
    print(f"  [Stage 4] ground-truth fraud rate = {rate:.3f} (target {target})")
    return fr


LIFECYCLE = ["manufacturing", "quality_test", "packaging", "warehouse_in",
             "shipment", "distributor_receipt", "pharmacy_receipt", "sale"]


def gen_events(cfg, batches, medicines, fraud, entities, rng):
    med = medicines.to_pandas().set_index("medicine_id")
    fr = fraud.to_pandas().set_index("batch_id")
    hc = cfg["cold_chain"]
    hard = cfg["hard_cases"]
    detection_rate = cfg["fraud"]["detection_rate"]
    date_start = datetime.fromisoformat(cfg["date_start"])

    events = []
    for b in batches.iter_rows(named=True):
        bid = b["batch_id"]
        m = med.loc[b["medicine_id"]]
        f = fr.loc[bid]
        is_fraud = f["is_fraud_ground_truth"]
        ftype = f["fraud_type"]
        cold = bool(m["is_cold_chain"])
        n_legs = int(rng.integers(1, 5))
        t = datetime.fromisoformat(b["production_date"]) + timedelta(hours=int(rng.integers(1, 48)))
        seq = LIFECYCLE.copy()
        for leg in range(n_legs):
            for step in seq:
                t += timedelta(hours=float(rng.gamma(2.0, 6.0)))
                temp = None
                if cold:
                    temp = round(float(rng.normal(5, 1.2)), 2)
                else:
                    temp = round(float(rng.normal(20, 2.5)), 2)
                qr_ok = True
                seal = True
                gps_missing = rng.random() < hard["mnar_missing_genuine"]
                suspicious = False

                if (not is_fraud) and rng.random() < hard["suspicious_genuine_share"]:
                    suspicious = True
                    roll = rng.random()
                    if cold and roll < 0.5:
                        temp = round(float(rng.uniform(8.5, 11)), 2)
                    elif roll < 0.8:
                        qr_ok = False

                masked = False
                if is_fraud:
                    if rng.random() < hard["masked_fraud_share"]:
                        masked = True
                    else:
                        if ftype in ("fake_qr", "counterfeit", "duplicate_batch"):
                            qr_ok = rng.random() > 0.7
                        if ftype in ("tampering", "theft"):
                            seal = rng.random() > 0.6
                        if ftype == "temperature" and cold:
                            temp = round(float(rng.uniform(9, 15)), 2)
                    if rng.random() < hard["mnar_missing_tampered"]:
                        gps_missing = True

                if cold and (not is_fraud) and (not suspicious):
                    if rng.random() < hc["excursion_rate"] * 0.3:
                        temp = round(float(rng.uniform(8.2, 9.5)), 2)

                events.append({
                    "batch_id": bid,
                    "country": b["country_of_origin"],
                    "event_type": step,
                    "leg": leg,
                    "timestamp": t.isoformat(),
                    "temperature": temp,
                    "humidity": round(float(rng.uniform(30, 70)), 1),
                    "gps_lat": None if gps_missing else round(float(rng.uniform(21, 34)), 4),
                    "gps_lng": None if gps_missing else round(float(rng.uniform(39, 74)), 4),
                    "qr_verified": qr_ok,
                    "rfid_scanned": bool(rng.random() > 0.05),
                    "seal_intact": seal,
                    "weight": round(float(rng.normal(10, 0.3)), 3),
                    "door_open": bool(rng.random() < 0.05),
                    "battery_level": int(rng.integers(20, 100)),
                    "sensor_id": f"SENS_{rng.integers(1000,9999)}",
                    "is_fraud_ground_truth": bool(is_fraud),
                    "fraud_type": ftype,
                    "is_masked": masked,
                    "is_suspicious_genuine": suspicious,
                })

    ev = pl.DataFrame(events, infer_schema_length=len(events)).sort("timestamp")

    det = []
    for row in ev.iter_rows(named=True):
        if row["is_fraud_ground_truth"]:
            det.append(rng.random() < detection_rate)
        else:
            det.append(False)
    ev = ev.with_columns(pl.Series("is_fraud_detected", det))

    prev = "0" * 64
    cur_hashes, prev_hashes = [], []
    for row in ev.iter_rows(named=True):
        payload = f"{row['batch_id']}{row['event_type']}{row['timestamp']}{prev}"
        h = hashlib.sha256(payload.encode()).hexdigest()
        prev_hashes.append(prev)
        cur_hashes.append(h)
        prev = h
    ev = ev.with_columns([
        pl.Series("previous_hash", prev_hashes),
        pl.Series("current_hash", cur_hashes),
    ])

    ev = ev.with_columns(pl.col("timestamp").str.to_datetime())
    ev = ev.sort("timestamp")
    ev = ev.with_columns(
        pl.col("batch_id").cum_count().over("batch_id").alias("batch_tx_index")
    )
    ev = ev.join(batches.select(["batch_id", "medicine_id"]), on="batch_id", how="left")
    ev = ev.join(medicines.select(["medicine_id", "storage_min", "storage_max"]),
                 on="medicine_id", how="left")
    ev = ev.with_columns(
        ((pl.col("temperature") > pl.col("storage_max")) |
         (pl.col("temperature") < pl.col("storage_min")))
        .cast(pl.Int8).alias("_excursion_flag")
    )
    ev = ev.with_columns(
        pl.col("_excursion_flag").cum_sum().over("batch_id").alias("_cum_exc"),
    )
    ev = ev.with_columns(
        (pl.col("_cum_exc") / pl.col("batch_tx_index")).alias("rolling_excursion_rate")
    ).drop(["_excursion_flag", "_cum_exc", "medicine_id", "storage_min", "storage_max"])
    ev = ev.with_columns(pl.col("timestamp").dt.to_string("%Y-%m-%dT%H:%M:%S").alias("timestamp"))
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    rng = np.random.default_rng(cfg["seed"])

    n_batches = cfg["scale"][cfg["scale"]["mode"]]["n_batches"]
    print(f"Mode: {cfg['scale']['mode']}  |  batches: {n_batches}")

    print("[Stage 1] entities...")
    entities = gen_entities(cfg, rng)
    print(f"  {len(entities)} entities")

    print("[Stage 2] supply chain graph...")
    G, _ = build_graph(entities, cfg, rng)
    print(f"  {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print("[Stage 3] medicines + batches...")
    medicines = gen_medicines(cfg, rng)
    batches = gen_batches(cfg, entities, medicines, rng, n_batches)

    print("[Stage 4] hidden fraud assignment...")
    fraud = assign_fraud(cfg, batches, entities, rng)

    print("[Stage 5-8] events, evidence, detection, hash chain...")
    events = gen_events(cfg, batches, medicines, fraud, entities, rng)
    print(f"  {len(events)} transactions generated")

    import os
    out = cfg["output"]["dir"]
    os.makedirs(out, exist_ok=True)
    entities.write_parquet(f"{out}/entities.parquet")
    medicines.write_parquet(f"{out}/medicines.parquet")
    batches.write_parquet(f"{out}/batches.parquet")
    fraud.write_parquet(f"{out}/fraud_events.parquet")
    events.write_parquet(f"{out}/transactions.parquet")
    events.write_csv(f"{out}/transactions.csv")
    entities.write_csv(f"{out}/entities.csv")
    print(f"\nDone. Files written to {out}/")
    print(f"  detected fraud rate = {events['is_fraud_detected'].mean():.3f}")


if __name__ == "__main__":
    main()
