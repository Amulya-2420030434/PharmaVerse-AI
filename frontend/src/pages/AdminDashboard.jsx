/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Boxes,
  Check,
  Clock,
  PackageSearch,
  RefreshCw,
  ShieldAlert,
  Truck,
  UserCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";

import api from "../services/api";
import { extractErrorMessage } from "../utils/error";

const statCards = [
  ["Users", "total_users", Users],
  ["Pending Approvals", "pending_registrations", UserPlus],
  ["Drugs", "total_drugs", PackageSearch],
  ["Batches", "total_batches", Boxes],
  ["In transit", "active_shipments", Truck],
  ["Delivered", "delivered_shipments", Activity],
  ["Expired batches", "expired_batches", ShieldAlert],
  ["Inactive QR", "inactive_qr_records", ShieldAlert],
  ["Overdue shipments", "overdue_in_transit_shipments", Truck],
];

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function ServiceStatus({ name, status }) {
  const healthy = status === "operational" || status === "available" || status === "enabled";
  return (
    <li className="flex items-center justify-between gap-3 border-b border-slate-100 py-3 last:border-0">
      <span className="text-sm font-medium text-slate-700">{name}</span>
      <span
        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
          healthy
            ? "bg-emerald-50 text-emerald-700"
            : status === "disabled"
            ? "bg-slate-100 text-slate-600"
            : "bg-amber-50 text-amber-800"
        }`}
      >
        {status || "unknown"}
      </span>
    </li>
  );
}

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Registration approvals state
  const [registrationRequests, setRegistrationRequests] = useState([]);
  const [loadingRequests, setLoadingRequests] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const loadRequests = useCallback(async () => {
    setLoadingRequests(true);
    try {
      const response = await api.get("/admin/registration-requests?status_filter=PENDING");
      setRegistrationRequests(response.data || []);
    } catch {
      // Non-blocking if approval table fails
    } finally {
      setLoadingRequests(false);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/admin/dashboard/summary");
      setSummary(response.data);
      await loadRequests();
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to load administration data."));
    } finally {
      setLoading(false);
    }
  }, [loadRequests]);

  useEffect(() => {
    load();
  }, [load]);

  const handleApprove = async (userId, username) => {
    setActionError("");
    setActionSuccess("");
    try {
      await api.post(`/admin/registration-requests/${userId}/approve`);
      setActionSuccess(`User '${username}' has been approved successfully.`);
      setRegistrationRequests((prev) => prev.filter((r) => r.id !== userId));
      load();
    } catch (err) {
      setActionError(extractErrorMessage(err, "Failed to approve user registration."));
    }
  };

  const handleReject = async (userId, username) => {
    setActionError("");
    setActionSuccess("");
    try {
      await api.post(`/admin/registration-requests/${userId}/reject`);
      setActionSuccess(`User '${username}' registration has been rejected.`);
      setRegistrationRequests((prev) => prev.filter((r) => r.id !== userId));
      load();
    } catch (err) {
      setActionError(extractErrorMessage(err, "Failed to reject user registration."));
    }
  };

  const counts = summary?.counts || {};
  const roleEntries = Object.entries(counts.users_by_role || {});
  const services = summary?.system_status || {};

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">Administration</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">Admin Dashboard</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            User access approvals, operational exceptions, and service health from persisted application data.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-60 hover:bg-slate-50 transition"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      {error && (
        <div role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Overview Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {statCards.map(([title, key, Icon]) => (
          <article key={key} className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-50 text-[#5a1725]">
              <Icon size={20} />
            </span>
            <div>
              <p className="text-sm text-slate-500">{title}</p>
              <p className="mt-1 text-2xl font-bold text-[#102a43]">{loading ? "…" : counts[key] ?? "—"}</p>
            </div>
          </article>
        ))}
      </div>

      {/* Pending Registration Approvals Section */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <UserCheck size={20} className="text-[#5a1725]" />
              <h2 className="text-lg font-bold text-[#102a43]">Pending Registration Approvals</h2>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              New accounts registered via Email or Google OAuth require administrator authorization before signing in.
            </p>
          </div>
          <span className="rounded-full bg-rose-50 px-3 py-1 text-xs font-bold text-[#5a1725]">
            {registrationRequests.length} Pending
          </span>
        </div>

        {actionSuccess && (
          <div className="mt-4 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-800 font-medium">
            {actionSuccess}
          </div>
        )}
        {actionError && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-xs text-red-700 font-medium">
            {actionError}
          </div>
        )}

        {loadingRequests ? (
          <p className="mt-5 text-sm text-slate-500">Loading registration requests…</p>
        ) : registrationRequests.length ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500 font-semibold">
                <tr>
                  <th className="px-4 py-3">Applicant / Username</th>
                  <th className="px-4 py-3">Email Address</th>
                  <th className="px-4 py-3">Organization</th>
                  <th className="px-4 py-3">Requested Role</th>
                  <th className="px-4 py-3">Method</th>
                  <th className="px-4 py-3">Requested At</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {registrationRequests.map((req) => (
                  <tr key={req.id} className="hover:bg-slate-50/60 transition">
                    <td className="px-4 py-3.5">
                      <p className="font-semibold text-[#102a43]">{req.full_name || req.username}</p>
                      <p className="text-xs text-slate-400">@{req.username}</p>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-700">{req.email}</td>
                    <td className="px-4 py-3.5 text-xs">{req.organization || "—"}</td>
                    <td className="px-4 py-3.5">
                      <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-800">
                        {req.role}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="rounded-full bg-slate-50 border border-slate-200 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                        {req.auth_provider === "google" ? "Google" : "Email"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400">{formatDate(req.created_at)}</td>
                    <td className="px-4 py-3.5 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => handleApprove(req.id, req.username)}
                        className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 transition"
                      >
                        <Check size={14} /> Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => handleReject(req.id, req.username)}
                        className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 transition"
                      >
                        <X size={14} /> Reject
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-slate-400">
            <Clock className="mx-auto text-slate-300" size={32} />
            <p className="mt-2 text-sm">No pending user registration requests at this time.</p>
          </div>
        )}
      </div>

      {/* Role Distribution & System Health */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-[#102a43]">User access by role</h2>
          <p className="mt-1 text-sm text-slate-500">Counts are grouped from stored user accounts.</p>
          {loading ? (
            <p className="mt-5 text-sm text-slate-500">Loading user roles…</p>
          ) : roleEntries.length ? (
            <ul className="mt-4 divide-y divide-slate-100">
              {roleEntries.map(([role, count]) => (
                <li key={role} className="flex justify-between py-3 text-sm">
                  <span className="font-medium text-slate-700">{role}</span>
                  <span className="font-semibold text-[#102a43]">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 text-sm text-slate-500">No user accounts are recorded.</p>
          )}
          {summary && (
            <p className="mt-3 text-xs text-slate-500">
              {counts.active_users} of {counts.total_users} accounts are active.
            </p>
          )}
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-[#102a43]">System health</h2>
          {loading ? (
            <p className="mt-5 text-sm text-slate-500">Checking service status…</p>
          ) : (
            <ul className="mt-3">
              <ServiceStatus name="PostgreSQL" status={services.database} />
              <ServiceStatus name="Hyperledger Fabric" status={services.fabric} />
              <ServiceStatus name="Deterministic AI" status={services.ai} />
              {Object.entries(services.fda || {}).map(([source, status]) => (
                <ServiceStatus key={source} name={`FDA ${source}`} status={status} />
              ))}
            </ul>
          )}
          {summary?.fda_checked_at && (
            <p className="mt-3 text-xs text-slate-500">
              FDA status checked {formatDate(summary.fda_checked_at)}.
            </p>
          )}
        </article>
      </div>

      {/* Shipment & Verification Activity */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-[#102a43]">Recent shipment activity</h2>
          {loading ? (
            <p className="mt-4 text-sm text-slate-500">Loading activity…</p>
          ) : summary?.recent_activity?.length ? (
            <ol className="mt-3 divide-y divide-slate-100">
              {summary.recent_activity.map((event) => (
                <li key={event.shipment_id} className="py-3">
                  <div className="flex flex-wrap justify-between gap-2 text-sm">
                    <span className="font-semibold text-[#102a43]">{event.shipment_id}</span>
                    <span className="text-slate-500">{event.status}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">
                    {event.source} → {event.destination}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">Record created {formatDate(event.created_at)}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-4 text-sm text-slate-500">No shipment activity is recorded.</p>
          )}
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-[#102a43]">Verification history</h2>
          <p className="mt-2 text-sm text-slate-600">
            {summary?.verification_history?.detail || "Loading verification persistence status…"}
          </p>
          <p className="mt-3 text-xs text-slate-500">
            No counterfeit verification count is shown because verification results are not persisted.
          </p>
        </article>
      </div>
    </section>
  );
}
