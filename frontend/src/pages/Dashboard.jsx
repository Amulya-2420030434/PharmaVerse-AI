import { useEffect, useState } from "react";

import DashboardHeader from "../components/common/DashboardHeader";
import RecentActivity from "../components/common/RecentActivity";
import RecentAlerts from "../components/common/RecentAlerts";
import StatCard from "../components/common/StatCard";
import SystemStatus from "../components/common/SystemStatus";
import RiskChart from "../components/charts/RiskChart";
import ShipmentChart from "../components/charts/ShipmentChart";
import api from "../services/api";
import { extractErrorMessage } from "../utils/error";

function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    api
      .get("/dashboard/summary")
      .then((response) => {
        if (active) setSummary(response.data);
      })
      .catch((err) => {
        if (active)
          setError(extractErrorMessage(err, "Unable to load dashboard data."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const stats = summary?.stats;

  const statCards = [
    {
      title: "Total Drugs",
      value: loading ? "…" : (stats?.total_drugs ?? "—"),
      description: loading
        ? "Loading…"
        : `Registered pharmaceutical products`,
      icon: "drugs",
      status: "info",
    },
    {
      title: "Active Shipments",
      value: loading ? "…" : (stats?.active_shipments ?? "—"),
      description: loading ? "Loading…" : "Shipments currently in transit",
      icon: "shipments",
      status: "neutral",
    },
    {
      title: "Verified Medicines",
      value: loading ? "…" : (stats?.verified_medicines ?? "—"),
      description: loading
        ? "Loading…"
        : "Batches with active QR or RFID identity",
      icon: "verified",
      status: "success",
    },
    {
      title: "Inactive Batches",
      value: loading ? "…" : (stats?.potential_counterfeits ?? "—"),
      description: loading ? "Loading…" : "Batches marked inactive in the database",
      icon: "counterfeits",
      status: stats?.potential_counterfeits > 0 ? "danger" : "neutral",
    },
    {
      title: "Persisted AI Alerts",
      value: loading ? "…" : (stats?.active_anomalies ?? "—"),
      description: loading
        ? "Loading…"
        : "No alert history is persisted; AI analysis runs on demand",
      icon: "anomalies",
      status: "neutral",
    },
    {
      title: "High-Risk Shipments",
      value: loading ? "…" : (stats?.high_risk_shipments ?? "—"),
      description: loading
        ? "Loading…"
        : "In-transit shipments past expected arrival",
      icon: "shipments",
      status: stats?.high_risk_shipments > 0 ? "danger" : "neutral",
    },
  ];

  return (
    <section>
      <DashboardHeader loading={loading} error={error} />

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((stat) => (
          <StatCard key={stat.title} {...stat} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <RiskChart data={summary?.risk_distribution ?? []} loading={loading} />
        <ShipmentChart
          data={summary?.shipment_status_distribution ?? []}
          loading={loading}
        />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <RecentAlerts alerts={summary?.recent_alerts ?? []} loading={loading} />
        <RecentActivity
          events={summary?.recent_activity ?? []}
          loading={loading}
        />
      </div>

      <div className="mt-6">
        <SystemStatus status={summary?.system_status ?? null} loading={loading} />
      </div>
    </section>
  );
}

export default Dashboard;
