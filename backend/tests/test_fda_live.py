from __future__ import annotations

from app.services.fda_reference import FDAReferenceService


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        import json

        return json.dumps(self.payload).encode("utf-8")


def make_payload(total: int = 10):
    return {
        "meta": {
            "last_updated": "2026-09-25",
            "results": {"total": total},
        },
        "results": [{"id": "sample"}],
    }


def test_live_summary_uses_all_three_sources():
    calls = []

    def opener(url, timeout):
        calls.append(url)
        return FakeResponse(make_payload(10))

    service = FDAReferenceService(
        timeout=2,
        cache_ttl=300,
        opener=opener,
    )

    result = service.live_summary()

    assert set(result["sources"]) == {
        "ndc",
        "shortages",
        "enforcement",
    }

    assert len(calls) == 3

    assert result["sources"]["ndc"]["status"] == "available"
    assert result["sources"]["shortages"]["status"] == "available"
    assert result["sources"]["enforcement"]["status"] == "available"


def test_freshness_labels_are_correct():
    service = FDAReferenceService(
        opener=lambda url, timeout: FakeResponse(make_payload()),
    )

    result = service.live_summary()

    assert result["sources"]["ndc"]["freshness"] == "DAILY"
    assert result["sources"]["shortages"]["freshness"] == "DAILY"
    assert result["sources"]["enforcement"]["freshness"] == "WEEKLY"


def test_source_counts_are_taken_from_fda_metadata():
    def opener(url, timeout):
        return FakeResponse(make_payload(123))

    service = FDAReferenceService(opener=opener)

    result = service.live_summary()

    assert result["sources"]["ndc"]["count"] == 123
    assert result["sources"]["shortages"]["count"] == 123
    assert result["sources"]["enforcement"]["count"] == 123


def test_cache_prevents_duplicate_upstream_calls():
    calls = []

    def opener(url, timeout):
        calls.append(url)
        return FakeResponse(make_payload())

    service = FDAReferenceService(
        cache_ttl=300,
        opener=opener,
    )

    service.live_summary()
    service.live_summary()

    assert len(calls) == 3


def test_upstream_failure_is_reported_without_fake_data():
    def opener(url, timeout):
        raise TimeoutError("FDA request timed out")

    service = FDAReferenceService(opener=opener)

    result = service.live_summary()

    for source in result["sources"].values():
        assert source["status"] == "unavailable"
        assert source["count"] is None
        assert source["retrieved_at"] is None
        assert "timed out" in source["error"].lower()


def test_malformed_json_is_reported():
    class BadResponse(FakeResponse):
        def read(self):
            return b"not-json"

    def opener(url, timeout):
        return BadResponse({})

    service = FDAReferenceService(opener=opener)

    result = service.live_summary()

    for source in result["sources"].values():
        assert source["status"] == "unavailable"
        assert source["count"] is None


def test_existing_adverse_event_search_still_works():
    service = FDAReferenceService(
        opener=lambda url, timeout: FakeResponse(
            {"results": [{"event": "sample"}]}
        )
    )

    result = service.search("Paracetamol", 5)

    assert result["source"] == "openFDA"
    assert result["results"] == [{"event": "sample"}]