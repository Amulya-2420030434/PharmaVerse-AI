/* eslint-disable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import { extractErrorMessage } from "../utils/error";

export default function ApiResourcePage({ title, endpoint, detailPath, actions = [] }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    api.get(endpoint).then((res) => {
      const value = res.data;
      setItems(Array.isArray(value) ? value : value?.items || []);
    }).catch((err) => setError(extractErrorMessage(err, `Unable to load ${title.toLowerCase()}.`)))
      .finally(() => setLoading(false));
  };
  useEffect(load, [endpoint]);
  return <section>
    <h1 className="text-3xl font-bold text-[#102a43]">{title}</h1>
    {error && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    {loading ? <p className="mt-6 text-sm text-slate-500">Loading...</p> :
      items.length === 0 ? <p className="mt-6 rounded-xl border border-dashed p-8 text-center text-sm text-slate-500">No records available.</p> :
      <div className="mt-6 overflow-x-auto rounded-xl border bg-white"><table className="w-full text-left text-sm">
        <tbody>{items.map((item, index) => {
          const id = item.drug_id || item.batch_id || item.shipment_id || item.qr_id || item.rfid_id || item.id || index;
          return <tr key={id} className="border-b last:border-0"><td className="px-4 py-3 font-medium">
            {detailPath ? <Link className="text-[#5a1725]" to={`${detailPath}/${encodeURIComponent(id)}`}>{id}</Link> : id}
          </td><td className="px-4 py-3 text-slate-600">{Object.entries(item).filter(([key]) => key !== "id").slice(0, 4).map(([k,v]) => `${k}: ${v ?? "—"}`).join(" · ")}</td>
          </tr>;
        })}</tbody>
      </table></div>}
    {actions.length > 0 && <p className="mt-4 text-xs text-slate-500">{actions.join(" · ")}</p>}
  </section>;
}
