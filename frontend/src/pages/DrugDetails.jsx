import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import api from "../services/api";
import { extractErrorMessage } from "../utils/error";

export default function DrugDetails() {
  const { id } = useParams();
  const [drug, setDrug] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/drugs/${encodeURIComponent(id)}`)
      .then((response) => setDrug(response.data))
      .catch((requestError) => setError(extractErrorMessage(requestError, "Unable to load drug details.")))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <section>
      <Link to="/drugs" className="text-sm font-medium text-[#5a1725]">← Back to drugs</Link>
      <h1 className="mt-4 text-3xl font-bold text-[#102a43]">Drug Details</h1>
      {error && <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {loading && <p role="status" className="mt-5 text-sm text-slate-500">Loading drug details…</p>}
      {drug && (
        <div className="mt-6 grid gap-4 rounded-xl border border-slate-200 bg-white p-6 sm:grid-cols-2">
          {Object.entries(drug).map(([key, value]) => (
            <div key={key} className="border-b border-slate-100 py-3">
              <dt className="text-xs font-bold uppercase tracking-wider text-slate-400">{key.replaceAll("_", " ")}</dt>
              <dd className="mt-1 break-words text-sm text-slate-700">{value === null || value === "" ? "—" : String(value)}</dd>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
