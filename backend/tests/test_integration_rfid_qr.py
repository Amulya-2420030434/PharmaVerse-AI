"""Regression tests for public batch_id vs database UUID handling.

Bug class: RFID/QR/shipment creation must look a batch up by its *public*
``batch_id`` (e.g. BATCH-TEST-001) and store its internal UUID as the foreign
key.  These tests run against real models, so comparing the wrong column
(``Batch.id`` instead of ``Batch.batch_id``) fails them.
"""

RFID = {
    "rfid_id": "RFID-TEST-0001",
    "batch_id": "BATCH-TEST-001",
    "tag_value": "RFID-TEST-0001",
    "status": "ACTIVE",
}


def test_rfid_is_created_from_public_batch_id(client, seeded):
    response = client.post("/api/rfid", headers=seeded["mfr"], json=RFID)

    assert response.status_code == 201, response.text
    body = response.json()
    # The FK stores the internal UUID, which differs from the public id.
    assert body["batch_id"] == seeded["batch"]["id"]
    assert body["batch_id"] != "BATCH-TEST-001"
    assert body["status"] == "ACTIVE"


def test_rfid_get_list_and_deactivate(client, seeded):
    mfr = seeded["mfr"]
    client.post("/api/rfid", headers=mfr, json=RFID)

    assert client.get("/api/rfid/RFID-TEST-0001", headers=mfr).status_code == 200
    assert len(client.get("/api/rfid", headers=mfr).json()) == 1

    deactivated = client.post("/api/rfid/RFID-TEST-0001/deactivate", headers=mfr)
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"


def test_rfid_rejects_internal_uuid_with_helpful_message(client, seeded):
    response = client.post(
        "/api/rfid",
        headers=seeded["mfr"],
        json={**RFID, "batch_id": seeded["batch"]["id"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "public batch identifier" in response.json()["error"]["message"]


def test_rfid_unknown_batch_is_plain_404(client, seeded):
    response = client.post(
        "/api/rfid", headers=seeded["mfr"], json={**RFID, "batch_id": "NOPE"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Batch not found"


def test_rfid_batch_id_surrounding_whitespace_is_ignored(client, seeded):
    response = client.post(
        "/api/rfid",
        headers=seeded["mfr"],
        json={**RFID, "batch_id": "  BATCH-TEST-001 "},
    )

    assert response.status_code == 201


def test_batch_ids_are_stored_trimmed(client, seeded):
    response = client.post(
        "/api/batches",
        headers=seeded["mfr"],
        json={
            "batch_id": "  BATCH-PADDED  ",
            "drug_id": "DRUG-PARA-500",
            "manufacturing_date": "2026-01-01",
            "expiry_date": "2028-01-01",
            "quantity": 5,
        },
    )

    assert response.status_code == 201
    assert response.json()["batch_id"] == "BATCH-PADDED"
    assert client.post(
        "/api/rfid",
        headers=seeded["mfr"],
        json={**RFID, "rfid_id": "RFID-PAD", "batch_id": "BATCH-PADDED"},
    ).status_code == 201


def test_rfid_duplicate_and_invalid_status(client, seeded):
    mfr = seeded["mfr"]
    assert client.post("/api/rfid", headers=mfr, json=RFID).status_code == 201

    assert client.post("/api/rfid", headers=mfr, json=RFID).status_code == 409
    bad = client.post(
        "/api/rfid", headers=mfr, json={**RFID, "rfid_id": "R2", "status": "zzz"}
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"


def test_rfid_write_and_deactivate_are_role_restricted(client, seeded, make_user):
    _, distributor = make_user("DISTRIBUTOR")
    client.post("/api/rfid", headers=seeded["mfr"], json=RFID)

    assert client.post("/api/rfid", headers=distributor, json={**RFID, "rfid_id": "R9"}).status_code == 403
    assert client.post("/api/rfid/RFID-TEST-0001/deactivate", headers=distributor).status_code == 403
    assert client.post("/api/rfid", json=RFID).status_code == 401


def test_qr_lifecycle_uses_public_batch_id(client, seeded, make_user):
    mfr = seeded["mfr"]
    qr = {
        "qr_id": "QR-TEST-0001",
        "batch_id": "BATCH-TEST-001",
        "encoded_value": "https://example.test/v/BATCH-TEST-001",
    }

    created = client.post("/api/qr", headers=mfr, json=qr)
    assert created.status_code == 201, created.text
    assert created.json()["batch_id"] == seeded["batch"]["id"]
    assert client.get("/api/qr/QR-TEST-0001", headers=mfr).status_code == 200
    assert client.post("/api/qr", headers=mfr, json=qr).status_code == 409
    assert client.post(
        "/api/qr",
        headers=mfr,
        json={**qr, "qr_id": "QR-U", "batch_id": seeded["batch"]["id"]},
    ).status_code == 404

    _, distributor = make_user("DISTRIBUTOR")
    assert client.post("/api/qr/QR-TEST-0001/deactivate", headers=distributor).status_code == 403
    assert client.post("/api/qr/QR-TEST-0001/deactivate", headers=mfr).status_code == 200


def test_batch_get_is_by_public_id_only(client, seeded):
    mfr = seeded["mfr"]

    assert client.get("/api/batches/BATCH-TEST-001", headers=mfr).status_code == 200
    assert client.get(f"/api/batches/{seeded['batch']['id']}", headers=mfr).status_code == 404


def test_batch_rejects_non_positive_quantity(client, seeded):
    response = client.post(
        "/api/batches",
        headers=seeded["mfr"],
        json={
            "batch_id": "B-NEG",
            "drug_id": "DRUG-PARA-500",
            "manufacturing_date": "2026-01-01",
            "expiry_date": "2028-01-01",
            "quantity": 0,
        },
    )

    assert response.status_code == 422


def test_overlong_drug_id_is_a_validation_error_not_a_500(client, seeded):
    response = client.post(
        "/api/drugs",
        headers=seeded["mfr"],
        json={"drug_id": "x" * 200, "name": "n", "manufacturer": "m"},
    )

    assert response.status_code == 422
