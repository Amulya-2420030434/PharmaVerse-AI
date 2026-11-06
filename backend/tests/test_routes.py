from app.main import app


def test_required_api_routes_are_registered():
    paths = app.openapi()["paths"]

    assert set(paths["/api/auth/register"]) >= {"post"}
    assert set(paths["/api/auth/login"]) >= {"post"}
    assert set(paths["/api/auth/me"]) >= {"get"}
    assert set(paths["/api/drugs"]) >= {"get", "post"}
    assert set(paths["/api/drugs/{drug_id}"]) >= {"get"}
    assert set(paths["/api/batches"]) >= {"get", "post"}
    assert set(paths["/api/batches/{batch_id}"]) >= {"get"}
    assert set(paths["/api/shipments"]) >= {"get", "post"}
    assert set(paths["/api/shipments/{shipment_id}"]) >= {"get"}
    assert set(paths["/api/shipments/{shipment_id}/depart"]) >= {"post"}
    assert set(paths["/api/shipments/{shipment_id}/receive"]) >= {"post"}
    assert set(paths["/api/shipments/{shipment_id}/transfer"]) >= {"post"}
    assert set(paths["/api/qr"]) >= {"get", "post"}
    assert set(paths["/api/qr/{qr_id}"]) >= {"get"}
    assert set(paths["/api/qr/{qr_id}/deactivate"]) >= {"post"}
    assert set(paths["/api/rfid"]) >= {"get", "post"}
    assert set(paths["/api/rfid/{rfid_id}"]) >= {"get"}
    assert set(paths["/api/rfid/{rfid_id}/deactivate"]) >= {"post"}
    assert set(paths["/api/verification/verify"]) >= {"post"}
    assert set(paths["/api/audit/batch/{batch_id}"]) >= {"get"}
