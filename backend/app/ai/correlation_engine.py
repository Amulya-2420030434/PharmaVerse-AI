from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable, List

from .models import AnomalyRecord, CorrelationRecord, anomaly_evidence_id, ensure_utc

CORRELATION_WINDOW_MINUTES = 60
_CORRELATION_WINDOW = timedelta(minutes=CORRELATION_WINDOW_MINUTES)


class CorrelationEngine:
    @staticmethod
    def events_for_event(
        anomalies: Iterable[AnomalyRecord],
        batch_id: str | None,
        assessment_time: datetime,
    ) -> List[AnomalyRecord]:
        target = ensure_utc(assessment_time)
        start = target - _CORRELATION_WINDOW
        if batch_id is None:
            return [
                item
                for item in anomalies
                if item.timestamp is not None and ensure_utc(item.timestamp) == target
            ]
        return [
            item
            for item in anomalies
            if item.batch_id == batch_id
            and item.timestamp is not None
            and start <= ensure_utc(item.timestamp) <= target
        ]

    def correlate(
        self,
        anomalies: Iterable[AnomalyRecord],
        assessment_time: datetime | None = None,
    ) -> List[CorrelationRecord]:
        by_batch: dict[str, list[AnomalyRecord]] = defaultdict(list)
        for anomaly in anomalies:
            if anomaly.batch_id is not None and anomaly.timestamp is not None:
                by_batch[anomaly.batch_id].append(anomaly)

        records: List[CorrelationRecord] = []
        for batch_id, batch_anomalies in by_batch.items():
            target = ensure_utc(assessment_time) if assessment_time else max(
                ensure_utc(item.timestamp)
                for item in batch_anomalies
                if item.timestamp is not None
            )
            window_events = self.events_for_event(
                batch_anomalies,
                batch_id,
                target,
            )
            factors = sorted({item.factor for item in window_events})
            if len(factors) < 2:
                continue

            ordered = sorted(
                window_events,
                key=lambda item: ensure_utc(item.timestamp),
            )
            event_types = sorted({item.type for item in ordered})
            evidence_ids = sorted({anomaly_evidence_id(item) for item in ordered})
            records.append(
                CorrelationRecord(
                    shipment_id=ordered[-1].shipment_id,
                    batch_id=batch_id,
                    event_types=event_types,
                    factors=factors,
                    confidence=round(min(0.95, 0.45 + len(ordered) * 0.1), 2),
                    summary=(
                        "Distinct anomaly factors are present in the same batch "
                        "within the preceding 60 minutes."
                    ),
                    evidence={
                        "event_count": len(ordered),
                        "factors": factors,
                        "evidence_ids": evidence_ids,
                        "window_minutes": CORRELATION_WINDOW_MINUTES,
                        "assessment_time": target,
                        "start": ordered[0].timestamp,
                        "end": ordered[-1].timestamp,
                    },
                )
            )
        return records
