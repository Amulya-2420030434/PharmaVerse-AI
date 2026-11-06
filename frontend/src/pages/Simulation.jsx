/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useState } from "react";
import StructuredData from "../components/common/StructuredData";
import api from "../services/api";
import { extractErrorMessage } from "../utils/error";

export default function Simulation() {
  const [scenario, setScenario] = useState("normal");
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const request = async (method, path, body) => {
    setError("");
    setLoading(true);
    try {
      const response = await api[method](path, body);
      if (path === "/simulation/scenario") setResult(response.data);
      else setStatus(response.data);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Simulation request failed."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    request("get", "/simulation/status");
  }, []);

  return (
    <section>
      <h1 className="text-3xl font-bold text-[#102a43]">Simulation</h1>
      <p className="mt-2 text-sm text-slate-600">Control the supported simulation lifecycle and execute a named scenario.</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <button disabled={loading} onClick={() => request("post", "/simulation/start", { scenario })} className="rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">Start</button>
        <button disabled={loading} onClick={() => request("post", "/simulation/stop")} className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-60">Stop</button>
        <button disabled={loading} onClick={() => request("get", "/simulation/status")} className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-60">Refresh status</button>
        <input value={scenario} onChange={(event) => setScenario(event.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm" aria-label="Simulation scenario" />
        <button disabled={loading} onClick={() => request("post", "/simulation/scenario", { scenario })} className="rounded-lg border border-[#5a1725] px-4 py-2.5 text-sm font-semibold text-[#5a1725] disabled:opacity-60">Run scenario</button>
      </div>
      {error && <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {loading && <p role="status" className="mt-5 text-sm text-slate-500">Waiting for simulation response…</p>}
      {status && <article className="mt-5 rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold text-[#102a43]">Simulation status</h2><StructuredData value={status} className="mt-4" /></article>}
      {result && <article className="mt-5 rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold text-[#102a43]">Scenario output</h2><StructuredData value={result} className="mt-4" /></article>}
    </section>
  );
}
