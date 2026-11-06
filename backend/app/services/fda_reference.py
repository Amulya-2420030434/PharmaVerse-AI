from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlencode, quote
from urllib.request import urlopen


class FDAReferenceService:
    """Read-only openFDA client for reference and live pharmaceutical intelligence."""

    ADVERSE_EVENT_URL = "https://api.fda.gov/drug/event.json"

    LIVE_SOURCES = {
        "ndc": {
            "name": "FDA NDC Directory",
            "endpoint": "https://api.fda.gov/drug/ndc.json",
            "freshness": "DAILY",
            "params": {"limit": 1},
        },
        "shortages": {
            "name": "FDA Drug Shortages",
            "endpoint": "https://api.fda.gov/drug/shortages.json",
            "freshness": "DAILY",
            "params": {"limit": 1},
        },
        "enforcement": {
            "name": "FDA Drug Enforcement",
            "endpoint": "https://api.fda.gov/drug/enforcement.json",
            "freshness": "WEEKLY",
            "params": {
                "sort": "report_date:desc",
                "limit": 1,
            },
        },
    }

    def __init__(
        self,
        timeout: float | None = None,
        cache_ttl: float | None = None,
        opener=urlopen,
    ):
        self.timeout = (
            float(os.getenv("FDA_API_TIMEOUT_SECONDS", "8"))
            if timeout is None
            else timeout
        )
        self.cache_ttl = (
            float(os.getenv("FDA_CACHE_TTL_SECONDS", "300"))
            if cache_ttl is None
            else cache_ttl
        )
        self.opener = opener

        self._cache: dict[str, dict] = {}
        self._cache_lock = Lock()

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _build_url(self, endpoint: str, params: dict[str, object]) -> str:
        return f"{endpoint}?{urlencode(params)}"

    def _fetch_json(self, url: str) -> dict:
        with self.opener(url, timeout=self.timeout) as response:
            raw = response.read()

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        payload = json.loads(raw)

        if not isinstance(payload, dict):
            raise ValueError("FDA response was not a JSON object")

        return payload

    def search(self, drug_name: str, limit: int = 10) -> dict:
        """Existing adverse-event search API. Preserved for compatibility."""
        if not drug_name.strip():
            return {
                "results": [],
                "source": "openFDA",
                "error": "drug_name is required",
            }

        query = quote(
            f'patient.drug.medicinalproduct:"{drug_name.strip()}"'
        )
        url = (
            f"{self.ADVERSE_EVENT_URL}"
            f"?search={query}"
            f"&limit={max(1, min(limit, 100))}"
        )

        try:
            payload = self._fetch_json(url)
            return {
                "results": payload.get("results", []),
                "source": "openFDA",
                "url": url,
            }
        except Exception as exc:
            return {
                "results": [],
                "source": "openFDA",
                "url": url,
                "error": str(exc),
            }

    def _cached(self, source_key: str) -> dict | None:
        with self._cache_lock:
            entry = self._cache.get(source_key)

            if not entry:
                return None

            if time.monotonic() >= entry["expires_at"]:
                self._cache.pop(source_key, None)
                return None

            cached_result = dict(entry["result"])
            cached_result["cached"] = True
            return cached_result

    def _store_cache(self, source_key: str, result: dict) -> dict:
        with self._cache_lock:
            self._cache[source_key] = {
                "expires_at": time.monotonic() + self.cache_ttl,
                "result": dict(result),
            }

        result = dict(result)
        result["cached"] = False
        return result

    def _fetch_live_source(self, source_key: str) -> dict:
        source = self.LIVE_SOURCES[source_key]

        cached = self._cached(source_key)
        if cached is not None:
            return cached

        checked_at = self._utc_now()
        url = self._build_url(source["endpoint"], source["params"])

        try:
            payload = self._fetch_json(url)

            meta = payload.get("meta") or {}
            meta_results = meta.get("results") or {}

            total = meta_results.get("total")
            if not isinstance(total, int):
                results = payload.get("results") or []
                total = len(results)

            result = {
                "name": source["name"],
                "status": "available",
                "freshness": source["freshness"],
                "source_endpoint": source["endpoint"],
                "retrieved_at": checked_at,
                "source_last_updated": meta.get("last_updated"),
                "count": total,
                "cached": False,
                "error": None,
            }

            return self._store_cache(source_key, result)

        except Exception as exc:
            return {
                "name": source["name"],
                "status": "unavailable",
                "freshness": source["freshness"],
                "source_endpoint": source["endpoint"],
                "retrieved_at": None,
                "source_last_updated": None,
                "count": None,
                "cached": False,
                "error": str(exc),
            }

    def live_summary(self) -> dict:
        """Retrieve current FDA source availability and summary metadata."""
        checked_at = self._utc_now()

        return {
            "checked_at": checked_at,
            "sources": {
                "ndc": self._fetch_live_source("ndc"),
                "shortages": self._fetch_live_source("shortages"),
                "enforcement": self._fetch_live_source("enforcement"),
            },
        }