"""Pydantic schemas for GET /api/dashboard/summary."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_drugs: int
    active_shipments: int
    verified_medicines: int
    potential_counterfeits: int
    active_anomalies: int
    high_risk_shipments: int


class RiskDistributionItem(BaseModel):
    name: str
    value: int
    fill: str


class ShipmentStatusItem(BaseModel):
    name: str
    value: int


class RecentAlertItem(BaseModel):
    id: str
    title: str
    shipment_id: str
    severity: str
    created_at: datetime


class RecentActivityItem(BaseModel):
    id: str
    description: str
    timestamp: str


class ServiceStatus(BaseModel):
    name: str
    status: str  # "operational" | "unavailable" | "disabled"
    detail: str


class SystemStatusInfo(BaseModel):
    api: ServiceStatus
    database: ServiceStatus
    blockchain: ServiceStatus
    ai_engine: ServiceStatus
    iot_simulator: ServiceStatus


class DashboardSummaryResponse(BaseModel):
    stats: DashboardStats
    risk_distribution: list[RiskDistributionItem]
    shipment_status_distribution: list[ShipmentStatusItem]
    recent_alerts: list[RecentAlertItem]
    recent_activity: list[RecentActivityItem]
    system_status: SystemStatusInfo
