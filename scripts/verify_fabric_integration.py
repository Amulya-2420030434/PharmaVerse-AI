import os
import sys
import json
from datetime import datetime, timezone, timedelta

# Set working directory and debug environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["DEBUG"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models.user import User
from app.models.drug import Drug
from app.models.batch import Batch
from app.models.shipment import Shipment
from app.services.auth_service import create_access_token, hash_password
from app.blockchain.fabric_client import FabricClient

def run_integration_verification():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    drug_id = f"PV_TEST_DRUG_{ts}"
    batch_id = f"PV_TEST_BATCH_{ts}"
    shipment_id = f"PV_TEST_SHIP_{ts}"
    qr_id = f"QR-MED-{batch_id}"
    rfid_id = f"RFID-MED-{batch_id}"

    print("=" * 70)
    print("PHARMAVERSE AI -> HYPERLEDGER FABRIC END-TO-END VERIFICATION")
    print("=" * 70)
    print(f"Synthetic Drug ID:     {drug_id}")
    print(f"Synthetic Batch ID:    {batch_id}")
    print(f"Synthetic Shipment ID: {shipment_id}")
    print(f"Synthetic QR ID:       {qr_id}")
    print(f"Synthetic RFID ID:     {rfid_id}")
    print("-" * 70)

    db = SessionLocal()
    try:
        # 1. Setup Auth User (ADMIN)
        user = db.query(User).filter(User.username == "fabric_integration_verifier").first()
        if not user:
            user = User(
                username="fabric_integration_verifier",
                email="fabric_verifier@pharmaverse.internal",
                password_hash=hash_password("IntegrationPass123!"),
                role="ADMIN",
                is_active=True,
                status="APPROVED",
                organization="PharmaVerse Quality Assurance",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_access_token(user_id=str(user.id), role=user.role)
        headers = {"Authorization": f"Bearer {token}"}
        client = TestClient(app)

        # 2. Check Fabric Gateway Health
        print("[1/9] Checking Fabric Gateway Health...")
        health = FabricClient().health()
        print(f"      Fabric Gateway: {health}")
        assert health.get("status") == "ok" or health.get("channel") == "mychannel"

        # 3. Drug Registration
        print(f"[2/9] Registering Drug '{drug_id}' (dual-write to Fabric & DB)...")
        drug_payload = {
            "drug_id": drug_id,
            "name": f"Synthetic Test Drug {ts}",
            "generic_name": "Syntheticum Verification",
            "manufacturer": "PharmaVerse Labs",
            "dosage_form": "TABLET",
            "strength": "500mg",
            "storage_min_temp": 15.0,
            "storage_max_temp": 25.0,
            "storage_min_humidity": 30.0,
            "storage_max_humidity": 60.0,
            "description": "Synthetic asset for Hyperledger Fabric dual-write verification",
            "expiry_period_days": 730,
        }
        res_drug = client.post("/api/drugs", headers=headers, json=drug_payload)
        assert res_drug.status_code == 201, f"Drug create failed: {res_drug.text}"
        drug_json = res_drug.json()
        drug_tx_id = drug_json.get("last_fabric_transaction_id")
        print(f"      Success! DB ID: {drug_json.get('id')}, Fabric TxID: {drug_tx_id}")
        assert drug_tx_id, "Missing Fabric transaction ID on registered drug"

        # Verify DB record
        db_drug = db.query(Drug).filter(Drug.drug_id == drug_id).first()
        assert db_drug and db_drug.last_fabric_transaction_id == drug_tx_id

        # 4. Batch Creation
        print(f"[3/9] Creating Batch '{batch_id}' (dual-write to Fabric & DB)...")
        mfg_date = datetime.now(timezone.utc).date()
        exp_date = mfg_date + timedelta(days=730)
        batch_payload = {
            "batch_id": batch_id,
            "drug_id": drug_id,
            "manufacturing_date": mfg_date.isoformat(),
            "expiry_date": exp_date.isoformat(),
            "quantity": 5000,
        }
        res_batch = client.post("/api/batches", headers=headers, json=batch_payload)
        assert res_batch.status_code == 201, f"Batch create failed: {res_batch.text}"
        batch_json = res_batch.json()
        batch_tx_id = batch_json.get("last_fabric_transaction_id")
        print(f"      Success! DB ID: {batch_json.get('id')}, Fabric TxID: {batch_tx_id}")
        assert batch_tx_id, "Missing Fabric transaction ID on batch"

        # Verify DB record
        db_batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
        assert db_batch and db_batch.last_fabric_transaction_id == batch_tx_id

        # 5. QR and RFID Identities
        print(f"[4/9] Assigning QR and RFID Identities for Batch...")
        res_qr = client.post(
            "/api/qr",
            headers=headers,
            json={
                "qr_id": qr_id,
                "batch_id": batch_id,
                "encoded_value": f"pharmaverse://batch/{batch_id}?qr={qr_id}",
                "status": "ACTIVE",
            },
        )
        assert res_qr.status_code == 201, f"QR create failed: {res_qr.text}"
        res_rfid = client.post(
            "/api/rfid",
            headers=headers,
            json={
                "rfid_id": rfid_id,
                "batch_id": batch_id,
                "tag_value": f"TAG-{rfid_id}",
                "status": "ACTIVE",
            },
        )
        assert res_rfid.status_code == 201, f"RFID create failed: {res_rfid.text}"
        print("      Success! QR and RFID registered in DB.")

        # 6. Shipment Creation and Lifecycle (Depart -> In Transit -> Receive -> Delivered)
        print(f"[5/9] Creating Shipment '{shipment_id}'...")
        res_shipment = client.post(
            "/api/shipments",
            headers=headers,
            json={
                "shipment_id": shipment_id,
                "batch_id": batch_id,
                "source": "Warehouse Central",
                "destination": "Regional Hospital Dispensary",
                "current_owner": "PharmaVerse Labs",
                "expected_arrival": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            },
        )
        assert res_shipment.status_code == 201, f"Shipment create failed: {res_shipment.text}"

        print(f"[6/9] Dispatching Shipment (Depart -> Fabric Ledger)...")
        res_depart = client.post(f"/api/shipments/{shipment_id}/depart", headers=headers)
        assert res_depart.status_code == 200, f"Shipment depart failed: {res_depart.text}"
        depart_tx_id = res_depart.json().get("last_fabric_transaction_id")
        print(f"      Success! Status: IN_TRANSIT, Fabric TxID: {depart_tx_id}")
        assert depart_tx_id, "Missing Fabric transaction ID on shipment departure"

        print(f"[7/9] Receiving Shipment (Receive -> Fabric Ledger)...")
        res_receive = client.post(f"/api/shipments/{shipment_id}/receive", headers=headers)
        assert res_receive.status_code == 200, f"Shipment receive failed: {res_receive.text}"
        receive_tx_id = res_receive.json().get("last_fabric_transaction_id")
        print(f"      Success! Status: DELIVERED, Fabric TxID: {receive_tx_id}")
        assert receive_tx_id, "Missing Fabric transaction ID on shipment receipt"

        # 7. Verification API Check (Real ledger confirmation)
        print(f"[8/9] Running Verification via /api/verification/verify...")
        res_verify = client.post(
            "/api/verification/verify",
            headers=headers,
            json={
                "batch_id": batch_id,
                "qr_id": qr_id,
                "rfid_id": rfid_id,
            },
        )
        assert res_verify.status_code == 200, f"Verification failed: {res_verify.text}"
        verify_json = res_verify.json()
        print(f"      Verification Status: {verify_json.get('verification_status')}")
        print(f"      Blockchain Status:   {verify_json.get('blockchain_status')}")
        assert verify_json.get("verification_status") == "AUTHENTIC"
        assert verify_json.get("blockchain_status") == "VERIFIED"

        # 8. Audit Trace & Fabric History
        print(f"[9/9] Querying Audit Trace with Fabric History...")
        res_trace = client.get(f"/api/audit/batch/{batch_id}", headers=headers)
        assert res_trace.status_code == 200, f"Audit trace failed: {res_trace.text}"
        trace_json = res_trace.json()
        print(f"      Trace Source: {trace_json.get('trace_source')}")
        fabric_history = trace_json.get("fabric_history") or []
        print(f"      Fabric History Entries Found: {len(fabric_history)}")
        for i, item in enumerate(fabric_history):
            tx_id = item.get("txId") or item.get("tx_id")
            val = item.get("value")
            print(f"        [{i+1}] TxID: {tx_id} | Value: {val}")

        assert trace_json.get("trace_source") == "POSTGRESQL_AND_FABRIC"
        assert len(fabric_history) >= 1, "Fabric ledger history must contain committed transactions"

        # 9. Reconcile endpoint
        print("-" * 70)
        print("Reconciliation verification via /api/blockchain/reconcile/batch/{batch_id}...")
        res_recon = client.post(f"/api/blockchain/reconcile/batch/{batch_id}", headers=headers)
        assert res_recon.status_code == 200, f"Reconcile failed: {res_recon.text}"
        recon_json = res_recon.json()["data"]
        print(f"      Reconciliation Result: {recon_json}")
        assert recon_json.get("reconciled") is True
        assert recon_json.get("action") in ("updated", "created")

        # Summary Proof
        print("=" * 70)
        print("ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 70)
        proof = {
            "status": "VERIFIED_SUCCESS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "synthetic_identifiers": {
                "drug_id": drug_id,
                "batch_id": batch_id,
                "shipment_id": shipment_id,
                "qr_id": qr_id,
                "rfid_id": rfid_id,
            },
            "transaction_ids": {
                "drug_registration": drug_tx_id,
                "batch_creation": batch_tx_id,
                "shipment_departure": depart_tx_id,
                "shipment_receipt": receive_tx_id,
            },
            "audit_trace_source": trace_json.get("trace_source"),
            "fabric_history_count": len(fabric_history),
            "reconciliation_status": "RECONCILED_IN_SYNC",
        }
        with open("fabric_integration_verification_proof.json", "w") as f:
            json.dump(proof, f, indent=2)
        print("Proof saved to fabric_integration_verification_proof.json")

    finally:
        db.close()

if __name__ == "__main__":
    run_integration_verification()
