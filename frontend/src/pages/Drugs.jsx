/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useMemo, useState } from "react";
import { ChevronRight, Package, Search } from "lucide-react";

import CreateButton from "../components/common/CreateButton";
import { useNavigate } from "react-router-dom";

import api from "../services/api";
import { extractErrorMessage } from "../utils/error";

export default function Drugs() {
  const navigate = useNavigate();
  const [drugs, setDrugs] = useState([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadDrugs = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/drugs");
      setDrugs(Array.isArray(response.data) ? response.data : []);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to load drugs."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDrugs();
  }, []);

  const filteredDrugs = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return drugs;
    return drugs.filter((drug) =>
      [drug.drug_id, drug.name, drug.generic_name, drug.manufacturer]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query)),
    );
  }, [drugs, search]);

  return (
    <section>
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">Traceability</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">Drug Management</h1>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mt-2 text-sm leading-6 text-slate-600">Registered drug identities and manufacturer metadata from the FastAPI service.</p>
        </div>
        <CreateButton endpoint="/drugs" title="Create Drug" onSuccess={loadDrugs} />
      </div>

      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by drug ID, name, or manufacturer" className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm outline-none focus:border-[#5a1725]" />
        </div>
      </div>

      {error && <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {loading ? (
        <div role="status" className="mt-5 rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">Loading drug records…</div>
      ) : filteredDrugs.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center text-sm text-slate-500">
          <Package className="mx-auto mb-3 text-slate-400" />
          {drugs.length ? "No drugs match this search." : "No drug records returned by the backend."}
        </div>
      ) : (
        <div className="mt-5 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Drug ID</th>
                  <th className="px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Name</th>
                  <th className="px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Manufacturer</th>
                  <th className="px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Dosage form</th>
                  <th className="px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Strength</th>
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDrugs.map((drug) => (
                  <tr key={drug.drug_id} className="hover:bg-slate-50">
                    <td className="px-5 py-4 font-medium text-[#102a43]">{drug.drug_id}</td>
                    <td className="px-5 py-4 text-slate-700">{drug.name}</td>
                    <td className="px-5 py-4 text-slate-700">{drug.manufacturer}</td>
                    <td className="px-5 py-4 text-slate-700">{drug.dosage_form || "—"}</td>
                    <td className="px-5 py-4 text-slate-700">{drug.strength || "—"}</td>
                    <td className="px-5 py-4 text-right">
                      <button type="button" onClick={() => navigate(`/drugs/${encodeURIComponent(drug.drug_id)}`)} className="rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-[#5a1725]" aria-label={`View ${drug.drug_id}`}>
                        <ChevronRight size={17} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
