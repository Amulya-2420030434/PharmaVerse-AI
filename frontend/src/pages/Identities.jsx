/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import CreateButton from "../components/common/CreateButton";
import api from "../services/api";
import { getStoredUser } from "../services/authService";
import { extractErrorMessage } from "../utils/error";
import { createQrPayload } from "../utils/qrPayload";

function formatDate(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
}

function StatusBadge({ status }) {
  const active = String(status).toUpperCase() === "ACTIVE";
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${active ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>
      {status || "Unknown"}
    </span>
  );
}

export default function Identities() {
  const [qrRecords, setQrRecords] = useState([]);
  const [rfidRecords, setRfidRecords] = useState([]);
  const [batchIds, setBatchIds] = useState({});
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creatingQr, setCreatingQr] = useState(false);
  const [qrIdInput, setQrIdInput] = useState("");
  const [batchIdInput, setBatchIdInput] = useState("");
  const [createError, setCreateError] = useState("");
  const [savingQr, setSavingQr] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const canCreate = ["ADMIN", "REGULATOR", "MANUFACTURER"].includes(getStoredUser()?.role);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [qrResponse, rfidResponse, batchResponse] = await Promise.all([
        api.get("/qr"),
        api.get("/rfid"),
        api.get("/batches"),
      ]);
      const batchRows = Array.isArray(batchResponse.data) ? batchResponse.data : [];
      const batchMap = Object.fromEntries(
        batchRows.map((batch) => [
          batch.id,
          batch.batch_id,
        ]),
      );
      setBatches(batchRows);
      setQrRecords(Array.isArray(qrResponse.data) ? qrResponse.data : []);
      setRfidRecords(Array.isArray(rfidResponse.data) ? rfidResponse.data : []);
      setBatchIds(batchMap);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to load QR and RFID records."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const refresh = () => setRefreshKey((value) => value + 1);
  const createQr = async (event) => {
    event.preventDefault();
    setSavingQr(true);
    setCreateError("");
    try {
      await api.post("/qr", {
        qr_id: qrIdInput.trim(),
        batch_id: batchIdInput,
        encoded_value: `${window.location.origin}/verification?qr_id=${encodeURIComponent(qrIdInput.trim())}`,
        status: "ACTIVE",
      });
      setCreatingQr(false);
      setQrIdInput("");
      setBatchIdInput("");
      refresh();
    } catch (requestError) {
      setCreateError(extractErrorMessage(requestError, "Unable to create the QR identity."));
    } finally {
      setSavingQr(false);
    }
  };

  return (
    <section>
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">Identity registry</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">QR & RFID Management</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            QR and RFID identities reference the operational batch records used for supply-chain verification.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" onClick={refresh} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-60">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
          {canCreate && (
            <>
              <button type="button" onClick={() => { setCreateError(""); setCreatingQr(true); }} className="rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white">Create QR</button>
              <CreateButton endpoint="/rfid" title="Create RFID Identity" label="Create RFID" onSuccess={refresh} />
            </>
          )}
        </div>
      </div>
      {creatingQr && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-[#102a43]/40 p-4">
          <form onSubmit={createQr} className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <h2 className="text-xl font-bold text-[#102a43]">Create QR verification identity</h2>
            <p className="mt-2 text-sm text-slate-600">The QR payload will contain the entered public QR ID and resolve through the existing verification API.</p>
            <label className="mt-5 block text-sm font-medium text-slate-700">Public QR ID
              <input required value={qrIdInput} onChange={(event) => setQrIdInput(event.target.value)} placeholder="QR-MED-000201" className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5" />
            </label>
            <label className="mt-4 block text-sm font-medium text-slate-700">Batch
              <select required value={batchIdInput} onChange={(event) => setBatchIdInput(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5">
                <option value="">Select a batch</option>
                {batches.map((batch) => <option key={batch.id} value={batch.batch_id}>{batch.batch_id}</option>)}
              </select>
            </label>
            {createError && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{createError}</p>}
            <div className="mt-6 flex justify-end gap-3">
              <button type="button" onClick={() => setCreatingQr(false)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm">Cancel</button>
              <button disabled={savingQr || !batches.length} className="rounded-lg bg-[#5a1725] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{savingQr ? "Creating…" : "Create QR"}</button>
            </div>
          </form>
        </div>
      )}
      {error && <div role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">Loading identity records…</div>
      ) : (
        <>
          <section>
            <h2 className="mb-4 text-xl font-semibold text-[#102a43]">QR codes</h2>
            {qrRecords.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">No QR records are available.</div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {qrRecords.map((record) => {
                  const payload = createQrPayload(record);
                  return (
                    <article key={record.qr_id} className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                      <div className="flex h-36 w-36 shrink-0 items-center justify-center rounded-lg border border-slate-100 bg-white p-2">
                        {payload ? (
                          <QRCodeSVG value={payload} size={128} level="M" includeMargin aria-label={`QR code for ${record.qr_id}`} />
                        ) : (
                          <span className="text-center text-xs text-red-700">Encoded payload unavailable</span>
                        )}
                      </div>
                      <dl className="min-w-0 space-y-2 text-sm">
                        <div><dt className="text-xs text-slate-500">QR ID</dt><dd className="break-all font-semibold text-[#102a43]">{record.qr_id}</dd></div>
                        <div><dt className="text-xs text-slate-500">Batch ID</dt><dd className="break-all text-slate-700">{batchIds[record.batch_id] || record.batch_id || "—"}</dd></div>
                        <div><dt className="text-xs text-slate-500">Status</dt><dd className="mt-1"><StatusBadge status={record.status} /></dd></div>
                        <div><dt className="text-xs text-slate-500">Created</dt><dd className="text-slate-700">{formatDate(record.created_at)}</dd></div>
                        <div><dt className="text-xs text-slate-500">Encoded value</dt><dd className="break-all text-xs text-slate-600">{record.encoded_value || "—"}</dd></div>
                      </dl>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
          <section className="mt-8">
            <h2 className="mb-4 text-xl font-semibold text-[#102a43]">RFID tags</h2>
            {rfidRecords.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">No RFID records are available.</div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="border-b border-slate-200 bg-slate-50">
                    <tr>{["RFID ID", "Batch ID", "Tag value", "Status", "Created"].map((label) => <th key={label} className="px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">{label}</th>)}</tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {rfidRecords.map((record) => (
                      <tr key={record.rfid_id}>
                        <td className="px-4 py-3 font-medium text-[#102a43]">{record.rfid_id}</td>
                        <td className="px-4 py-3 text-slate-700">{batchIds[record.batch_id] || record.batch_id || "—"}</td>
                        <td className="px-4 py-3 text-slate-700">{record.tag_value}</td>
                        <td className="px-4 py-3"><StatusBadge status={record.status} /></td>
                        <td className="px-4 py-3 text-slate-700">{formatDate(record.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </section>
  );
}
