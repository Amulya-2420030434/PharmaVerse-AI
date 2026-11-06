from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings


class FabricUnavailableError(RuntimeError):
    pass


class FabricGatewayError(RuntimeError):
    pass


class FabricAssetNotFoundError(FabricGatewayError):
    """The gateway is reachable but the requested ledger key is absent."""


class FabricDuplicateAssetError(FabricGatewayError):
    """The asset already exists on the ledger."""


class FabricInvalidTransitionError(FabricGatewayError):
    """The ledger lifecycle transition or ownership transfer is invalid."""


def _segment(value: str) -> str:
    """Percent-encode a client-supplied identifier for use as one URL path
    segment, so it cannot inject extra path components or query parameters
    into the gateway request."""
    return quote(str(value), safe="")


class FabricClient:
    def __init__(
        self,
        gateway_url: str | None = None,
        timeout: float | None = None,
        gateway_secret: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.gateway_url = (gateway_url or settings.fabric_gateway_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.fabric_gateway_timeout
        self.gateway_secret = (
            gateway_secret
            if gateway_secret is not None
            else settings.fabric_gateway_secret
        )
        self.transport = transport

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> Any:
        if not settings.fabric_enabled:
            raise FabricUnavailableError("Fabric integration is disabled")
        if not self.gateway_url:
            raise FabricUnavailableError("Fabric gateway URL is not configured")

        headers = {}
        if self.gateway_secret:
            headers["X-PharmaVerse-Service-Secret"] = self.gateway_secret

        try:
            with httpx.Client(
                base_url=self.gateway_url,
                timeout=self.timeout,
                headers=headers,
                transport=self.transport,
            ) as client:
                response = client.request(method, path, json=json)
        except httpx.TransportError as exc:
            raise FabricUnavailableError("Fabric gateway is unreachable") from exc
        except httpx.HTTPError as exc:
            raise FabricGatewayError("Fabric gateway request failed") from exc

        if response.status_code >= 400:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = None
            error = error_payload.get("error") if isinstance(error_payload, dict) else None
            error_code = error.get("code") if isinstance(error, dict) else None
            error_msg = error.get("message") if isinstance(error, dict) else None

            if error_code == "ASSET_NOT_FOUND" or response.status_code == 404:
                raise FabricAssetNotFoundError(error_msg or "Ledger asset not found")
            if error_code == "ASSET_ALREADY_EXISTS" or response.status_code == 409:
                raise FabricDuplicateAssetError(error_msg or "Ledger asset already exists")
            if error_code == "INVALID_TRANSITION" or (response.status_code == 400 and error_code):
                raise FabricInvalidTransitionError(error_msg or "Invalid ledger state transition")
            if error_code == "FABRIC_UNAVAILABLE" or response.status_code == 503:
                raise FabricUnavailableError(error_msg or "Fabric operation is unavailable")
            raise FabricGatewayError(
                error_msg or f"Fabric gateway returned HTTP {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FabricGatewayError("Fabric gateway returned invalid JSON") from exc

        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise FabricGatewayError("Fabric gateway returned an unsuccessful response")
        return payload.get("data")

    def get_drug(self, drug_id: str) -> Any:
        return self._request("GET", f"/api/drugs/{_segment(drug_id)}")

    def health(self) -> Any:
        """Return gateway health; the gateway exempts /health from auth."""
        return self._request("GET", "/health")

    def get_batch(self, batch_id: str) -> Any:
        return self._request("GET", f"/api/batches/{_segment(batch_id)}")

    def get_shipment(self, shipment_id: str) -> Any:
        return self._request("GET", f"/api/shipments/{_segment(shipment_id)}")

    def get_flag(self, flag_id: str) -> Any:
        return self._request("GET", f"/api/flags/{_segment(flag_id)}")

    def get_iot_event(self, event_id: str) -> Any:
        return self._request("GET", f"/api/iot-events/{_segment(event_id)}")

    def get_ai_alert(self, alert_id: str) -> Any:
        return self._request("GET", f"/api/ai-alerts/{_segment(alert_id)}")

    def get_batch_history(self, batch_id: str) -> Any:
        return self._request("GET", f"/api/batches/{_segment(batch_id)}/history")

    def verify_identity(self, batch_id: str, qr_id: str, rfid_id: str) -> Any:
        return self._request(
            "POST",
            "/api/verify-identity",
            {"batchId": batch_id, "qrId": qr_id, "rfidId": rfid_id},
        )

    def _write(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", path, payload)

    def register_drug(self, drug_id: str, name: str, strength: str, manufacturer: str) -> Any:
        return self._write("/api/drugs/register", {
            "drugId": drug_id, "name": name, "strength": strength,
            "manufacturer": manufacturer,
        })

    def create_batch(self, batch_id: str, drug_id: str, manufacturer: str,
                     quantity: int, manufactured_date: str, expiry_date: str,
                     qr_id: str | None = None, rfid_id: str | None = None) -> Any:
        payload = {
            "batchId": batch_id, "drugId": drug_id, "manufacturer": manufacturer,
            "quantity": str(quantity), "manufacturedDate": manufactured_date,
            "expiryDate": expiry_date,
        }
        if qr_id is not None and rfid_id is not None:
            payload.update({"qrId": qr_id, "rfidId": rfid_id})
        return self._write("/api/batches/create", payload)

    def assign_identity(self, batch_id: str, qr_id: str, rfid_id: str) -> Any:
        return self._write("/api/identities/assign", {
            "batchId": batch_id, "qrId": qr_id, "rfidId": rfid_id,
        })

    def record_iot_event(self, **payload: Any) -> Any:
        return self._write("/api/iot-events", payload)

    def record_ai_alert(self, **payload: Any) -> Any:
        return self._write("/api/ai-alerts", payload)

    def flag_drug(self, batch_id: str, reason: str, risk_level: str,
                  flagged_by: str) -> Any:
        return self._write("/api/flags", {
            "batchId": batch_id, "reason": reason,
            "riskLevel": risk_level, "flaggedBy": flagged_by,
        })

    def ship_drug(self, **payload: Any) -> Any:
        return self._write("/api/shipments/ship", payload)

    def receive_drug(self, shipment_id: str, receiver: str) -> Any:
        return self._write("/api/shipments/receive", {
            "shipmentId": shipment_id, "receiver": receiver,
        })

    def transfer_drug(self, batch_id: str, from_owner: str, to_owner: str) -> Any:
        return self._write("/api/shipments/transfer", {
            "batchId": batch_id, "from": from_owner, "to": to_owner,
        })
