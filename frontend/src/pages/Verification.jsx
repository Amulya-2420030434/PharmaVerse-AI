import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import QrScanner from "../components/common/QrScanner";
import api from "../services/api";
import { extractErrorMessage } from "../utils/error";
import { parseQrPayload } from "../utils/qrPayload";

const EMPTY_FORM = { qr_id: "", rfid_id: "", batch_id: "", drug_id: "" };

function statusStyles(status) {
  if (status === "AUTHENTIC") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "POTENTIAL_COUNTERFEIT" || status === "SUSPICIOUS") {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }
  if (status === "UNVERIFIED") return "border-amber-200 bg-amber-50 text-amber-900";
  return "border-red-200 bg-red-50 text-red-800";
}

export default function Verification() {
  const [searchParams] = useSearchParams();
  const initialQr = searchParams.get("qr_id");
  const initialBatch = searchParams.get("batch_id");

  // True when the URL contained at least one identifier param (from a QR scan
  // navigating here), regardless of whether the value was recognized.
  const arrivedFromQr = Boolean(initialQr || initialBatch);

  const initialPayload = initialQr
    ? parseQrPayload(initialQr)
    : initialBatch
      ? parseQrPayload(initialBatch)
      : null;

  const [form, setForm] = useState(() => ({ ...EMPTY_FORM, ...(initialPayload || {}) }));
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [scanMessage, setScanMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // Auto-submit once when the page is opened via a QR scan URL that produced a
  // recognized payload — so the user sees a result immediately rather than an
  // empty form.
  const autoSubmitted = useRef(false);
  useEffect(() => {
    if (!autoSubmitted.current && initialPayload) {
      autoSubmitted.current = true;
      const payload = Object.fromEntries(
        Object.entries({ ...EMPTY_FORM, ...initialPayload }).filter(([, v]) => v.trim()),
      );
      setLoading(true);
      api
        .post("/verification/verify", payload)
        .then((response) => setResult(response.data))
        .catch((requestError) =>
          setError(extractErrorMessage(requestError, "Unable to verify the supplied identifiers.")),
        )
        .finally(() => setLoading(false));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const onScan = useCallback((identifiers) => {
    setForm({ ...EMPTY_FORM, ...identifiers });
    setResult(null);
    setError("");
    setScanMessage("Scanned identifier added to the verification form.");
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, value]) => value.trim()),
      );
      if (Object.values(payload).length === 0) {
        setError(
          "Please enter at least one identifier (QR ID, RFID ID, Batch ID, or Drug ID) before verifying.",
        );
        return;
      }
      const response = await api.post("/verification/verify", payload);
      setResult(response.data);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to verify the supplied identifiers."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <h1 className="text-3xl font-bold text-[#102a43]">Medicine Verification</h1>
      <p className="mt-2 text-sm text-slate-600">
        Scan a QR or enter a QR, RFID, batch, or drug identifier. Every result comes from the verification API.
      </p>
      {arrivedFromQr && !initialPayload && (
        <div role="alert" className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          The scanned QR code could not be recognised as a PharmaVerse identifier.
          Enter a QR ID, RFID, batch ID, or drug ID manually below.
        </div>
      )}
      {loading && !result && (
        <p role="status" className="mt-4 text-sm text-slate-500">Checking identifiers…</p>
      )}
      <div className="mt-6">
        <QrScanner onScan={onScan} />
      </div>
      {scanMessage && <p className="mt-3 text-sm text-emerald-700">{scanMessage}</p>}
      <form onSubmit={submit} className="mt-5 grid gap-4 rounded-xl border border-slate-200 bg-white p-6 sm:grid-cols-2">
        {Object.keys(EMPTY_FORM).map((key) => (
          <label key={key} className="text-sm font-medium text-slate-700">
            {key.replaceAll("_", " ").toUpperCase()}
            <input
              value={form[key]}
              onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))}
              className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]"
            />
          </label>
        ))}
        <button disabled={loading} className="rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60 sm:col-span-2">
          {loading ? "Verifying…" : "Verify identifiers"}
        </button>
      </form>
      {error && <div role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {result && (
        <article className={`mt-5 rounded-xl border p-5 ${statusStyles(result.verification_status)}`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-bold">{result.verification_status?.replaceAll("_", " ")}</h2>
            <span className="text-xs font-semibold uppercase tracking-wide">
              Database: {result.database_status || "not confirmed"} · Ledger: {result.blockchain_status || "not checked"}
            </span>
          </div>
          <p className="mt-2 text-sm">{result.message}</p>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div><dt className="text-xs opacity-70">Batch</dt><dd className="font-medium">{result.batch_id || "Not resolved"}</dd></div>
            <div><dt className="text-xs opacity-70">Drug</dt><dd className="font-medium">{result.drug_id || "Not resolved"}</dd></div>
            <div><dt className="text-xs opacity-70">Batch status</dt><dd className="font-medium">{result.batch_status || "Not checked"}</dd></div>
            <div><dt className="text-xs opacity-70">Expiry date</dt><dd className="font-medium">{result.expiry_date || "Not available"}</dd></div>
          </dl>
          <div className="mt-4">
            <h3 className="text-xs font-bold uppercase tracking-wide opacity-70">Checks performed</h3>
            {result.checks_performed?.length ? (
              <ul className="mt-2 flex flex-wrap gap-2">
                {result.checks_performed.map((check) => <li key={check} className="rounded-full bg-white/70 px-3 py-1 text-xs">{check}</li>)}
              </ul>
            ) : <p className="mt-2 text-sm">No checks were performed.</p>}
          </div>
        </article>
      )}
    </section>
  );
}
