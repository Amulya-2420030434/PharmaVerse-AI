import { useState } from "react";
import StructuredData from "../components/common/StructuredData";
import api from "../services/api";
import { extractErrorMessage } from "../utils/error";
import { getStoredUser } from "../services/authService";

export default function Blockchain() {
  const [batchId, setBatchId] = useState("");
  const [data, setData] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const [loading, setLoading] = useState(false);
  const [fabricUnavailable, setFabricUnavailable] = useState(false);

  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState("");
  const [registerSuccess, setRegisterSuccess] = useState("");
  const [registerKind, setRegisterKind] = useState(null);

  const user = getStoredUser();
  const canRegister = user ? ["ADMIN", "REGULATOR", "MANUFACTURER"].includes(user.role) : false;

  const load = async (event) => {
    event.preventDefault();
    setHistoryError("");
    setData(null);
    setLoading(true);
    setFabricUnavailable(false);
    try {
      const response = await api.get(`/blockchain/batches/${encodeURIComponent(batchId.trim())}/history`);
      setData(response.data);
    } catch (requestError) {
      setFabricUnavailable(requestError?.response?.status === 503);
      setHistoryError(extractErrorMessage(requestError, "Unable to load blockchain history."));
    } finally {
      setLoading(false);
    }
  };

  const registerDrug = async (event) => {
    event.preventDefault();
    setRegisterError("");
    setRegisterSuccess("");
    setRegistering(true);
    try {
      const form = event.target.elements;
      const payload = {
        drug_id: form["drug_id"].value.trim(),
        name: form["name"].value.trim(),
        strength: form["strength"].value.trim(),
        manufacturer: form["manufacturer"].value.trim(),
      };
      const response = await api.post("/blockchain/writes/drugs", payload);
      setRegisterSuccess(
        `Drug ${payload.drug_id} registered on the ledger (transaction ${response.data.data?.transactionId ?? "submitted"}).`,
      );
      event.target.reset();
    } catch (requestError) {
      setRegisterError(extractErrorMessage(requestError, "Unable to register the drug on the ledger."));
    } finally {
      setRegistering(false);
    }
  };

  const registerBatch = async (event) => {
    event.preventDefault();
    setRegisterError("");
    setRegisterSuccess("");
    setRegistering(true);
    try {
      const form = event.target.elements;
      const qrId = form["qr_id"].value.trim();
      const rfidId = form["rfid_id"].value.trim();
      const payload = {
        batch_id: form["batch_id"].value.trim(),
        drug_id: form["drug_id"].value.trim(),
        manufacturer: form["manufacturer"].value.trim(),
        quantity: parseInt(form["quantity"].value, 10),
        manufactured_date: form["manufactured_date"].value.trim(),
        expiry_date: form["expiry_date"].value.trim(),
      };
      if ((qrId && !rfidId) || (!qrId && rfidId)) {
        setRegisterError("QR ID and RFID ID must both be provided together, or both left empty.");
        setRegistering(false);
        return;
      }
      if (payload.expiry_date <= payload.manufactured_date) {
        setRegisterError("Expiry date must be after manufactured date.");
        setRegistering(false);
        return;
      }
      if (!payload.quantity || payload.quantity <= 0) {
        setRegisterError("Quantity must be a positive integer.");
        setRegistering(false);
        return;
      }
      if (qrId && rfidId) {
        payload.qr_id = qrId;
        payload.rfid_id = rfidId;
      }
      const response = await api.post("/blockchain/writes/batches", payload);
      setRegisterSuccess(
        `Batch ${payload.batch_id} registered on the ledger (transaction ${response.data.data?.transactionId ?? "submitted"}).`,
      );
      event.target.reset();
    } catch (requestError) {
      setRegisterError(extractErrorMessage(requestError, "Unable to register the batch on the ledger."));
    } finally {
      setRegistering(false);
    }
  };

  const startDrugRegistration = () => setRegisterKind("drug");
  const startBatchRegistration = () => setRegisterKind("batch");
  const closeRegistration = () => {
    setRegisterKind(null);
    setRegisterError("");
    setRegisterSuccess("");
  };

  return (
    <section>
      <h1 className="text-3xl font-bold text-[#102a43]">Blockchain Explorer</h1>
      <p className="mt-2 text-sm text-slate-600">Read actual Fabric ledger history and register new drug/batch assets when the configured gateway is available.</p>
      <form onSubmit={load} className="mt-6 flex max-w-xl gap-3">
        <input required value={batchId} onChange={(event) => setBatchId(event.target.value)} placeholder="Batch ID" className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-[#5a1725]" />
        <button disabled={loading} className="rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{loading ? "Checking Fabric…" : "Load history"}</button>
      </form>
      {fabricUnavailable && (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">Fabric is disabled or unavailable. No ledger history is displayed.</p>
      )}
      {historyError && <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{historyError}</div>}
      {loading && <p role="status" className="mt-4 text-sm text-slate-500">Contacting the configured Fabric gateway…</p>}
      {data && (
        <article className="mt-5 rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="font-semibold text-[#102a43]">Gateway response for {batchId.trim()}</h2>
          <StructuredData value={data.data} className="mt-4" />
        </article>
      )}
      <section className="mt-12">
        <h2 className="text-xl font-bold text-[#102a43]">Register Ledger Asset</h2>
        <p className="mt-2 text-sm text-slate-600">Authorized roles: ADMIN, REGULATOR, MANUFACTURER. Registration writes to the Fabric ledger.</p>
        {!canRegister && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Your current role is not authorized to register ledger assets.
          </div>
        )}
        {canRegister && (
          <>
            <button
              type="button"
              onClick={startDrugRegistration}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-[#5a1725]"
            >
              Register Drug
            </button>
            <button
              type="button"
              onClick={startBatchRegistration}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-[#5a1725] ml-2"
            >
              Register Batch
            </button>
          </>
        )}
        {registerKind === "drug" && (
          <article className="mt-6 rounded-xl border border-slate-200 bg-white p-5">
            <h3 className="font-semibold text-[#102a43] mb-3">Register Drug</h3>
            <form onSubmit={registerDrug} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <label className="text-sm font-medium text-slate-700">
                Drug ID
                <input name="drug_id" required defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Name
                <input name="name" required defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Strength
                <input name="strength" required defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Manufacturer
                <input name="manufacturer" required defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <div className="sm:col-span-2">
                <button
                  type="submit"
                  disabled={registering}
                  className="rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {registering ? "Registering…" : "Register Drug on Ledger"}
                </button>
                <button
                  type="button"
                  onClick={closeRegistration}
                  className="ml-2 rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700"
                >
                  Cancel
                </button>
              </div>
            </form>
          </article>
        )}
        {registerKind === "batch" && (
          <article className="mt-6 rounded-xl border border-slate-200 bg-white p-5">
            <h3 className="font-semibold text-[#102a43] mb-3">Register Batch</h3>
            <form onSubmit={registerBatch} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <label className="text-sm font-medium text-slate-700">
                Batch ID
                <input name="batch_id" required defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Drug ID
                <input name="drug_id" required defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Manufacturer
                <input name="manufacturer" required defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Quantity
                <input name="quantity" required type="number" min="1" defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Manufactured Date
                <input name="manufactured_date" required type="date" defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Expiry Date
                <input name="expiry_date" required type="date" defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                QR ID (optional)
                <input name="qr_id" defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                RFID ID (optional)
                <input name="rfid_id" defaultValue="" className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 outline-none focus:border-[#5a1725]" />
              </label>
              <div className="sm:col-span-2">
                <button
                  type="submit"
                  disabled={registering}
                  className="rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {registering ? "Registering…" : "Register Batch on Ledger"}
                </button>
                <button
                  type="button"
                  onClick={closeRegistration}
                  className="ml-2 rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700"
                >
                  Cancel
                </button>
              </div>
            </form>
          </article>
        )}
        {registerError && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{registerError}</div>
        )}
        {registerSuccess && (
          <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{registerSuccess}</div>
        )}
      </section>
    </section>
  );
}
