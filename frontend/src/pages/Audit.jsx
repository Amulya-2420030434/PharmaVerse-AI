/* eslint-disable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../services/api";
import StructuredData from "../components/common/StructuredData";
import { extractErrorMessage } from "../utils/error";

export default function Audit() {
  const [params] = useSearchParams();
  const [batchId, setBatchId] = useState(params.get("batch_id") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async (event) => {
    event?.preventDefault();
    setError("");
    setData(null);
    setLoading(true);
    try {
      const response = await api.get(`/audit/batch/${encodeURIComponent(batchId.trim())}`);
      setData(response.data);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to load the batch audit trail."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (batchId) load();
  }, []);

  return (
    <section>
      <h1 className="text-3xl font-bold text-[#102a43]">Audit Trail</h1>
      <form onSubmit={load} className="mt-6 flex max-w-xl gap-3">
        <input required value={batchId} onChange={(event) => setBatchId(event.target.value)} placeholder="Batch ID" className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-[#5a1725]" />
        <button className="rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white">Load audit</button>
      </form>
      {error && <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {loading && <p role="status" className="mt-5 text-sm text-slate-500">Loading audit history…</p>}
      {data && <div className="mt-5 rounded-xl border border-slate-200 bg-white p-5"><StructuredData value={data} /></div>}
    </section>
  );
}
