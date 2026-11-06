/* eslint-disable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */
import { useEffect, useMemo, useState } from "react";
import { ChevronRight, RefreshCw, Search } from "lucide-react";

import api from "../../services/api";
import { extractErrorMessage } from "../../utils/error";

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function ApiResourceTable({
  title,
  description,
  endpoint,
  columns,
  searchKeys,
  getRowId,
  onRowClick,
  showIntro = true,
}) {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get(endpoint);
      setItems(Array.isArray(response.data) ? response.data : []);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, `Unable to load ${title.toLowerCase()}.`));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [endpoint]);

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return items;
    return items.filter((item) =>
      searchKeys.some((key) => formatValue(item[key]).toLowerCase().includes(query)),
    );
  }, [items, search, searchKeys]);

  return (
    <section>
      {showIntro ? (
        <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">API data</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">{title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{description}</p>
          </div>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-[#5a1725] disabled:opacity-60"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      ) : (
        <div className="mb-4 flex justify-end">
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-[#5a1725] disabled:opacity-60"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      )}

      <div className="mb-5 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="relative">
          <Search size={17} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={`Search ${title.toLowerCase()}...`}
            className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm outline-none focus:border-[#5a1725] focus:ring-2 focus:ring-[#5a1725]/10"
          />
        </div>
      </div>

      {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">Loading...</div>
      ) : filteredItems.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center text-sm text-slate-500">
          No records returned by the backend.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  {columns.map((column) => (
                    <th key={column.key} className="px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">{column.label}</th>
                  ))}
                  {onRowClick && <th />}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredItems.map((item) => (
                  <tr key={getRowId(item)} className="hover:bg-slate-50">
                    {columns.map((column) => (
                      <td key={column.key} className="px-5 py-4 text-slate-700">
                        {column.render ? column.render(item) : formatValue(item[column.key])}
                      </td>
                    ))}
                    {onRowClick && (
                      <td className="px-5 py-4 text-right">
                        <button type="button" onClick={() => onRowClick(item)} className="rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-[#5a1725]" aria-label={`View ${getRowId(item)}`}>
                          <ChevronRight size={17} />
                        </button>
                      </td>
                    )}
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
