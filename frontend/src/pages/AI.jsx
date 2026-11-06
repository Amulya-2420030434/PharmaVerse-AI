import { useEffect, useState } from "react";
import StructuredData from "../components/common/StructuredData";
import api from "../services/api";
import { extractErrorMessage } from "../utils/error";

const SCENARIOS = [
  ["normal", "Normal"],
  ["temperature_excursion", "Temperature excursion"],
  ["humidity_excursion", "Humidity excursion"],
  ["route_deviation", "Route deviation"],
  ["delayed_shipment", "Delayed shipment"],
  ["rfid_mismatch", "RFID mismatch"],
  ["qr_mismatch", "QR mismatch"],
  ["unauthorized_transfer", "Unauthorized transfer"],
  ["combined_high_risk", "Combined high risk"],
  ["expiry_violation", "Simulated expired product observation"],
];

const localDateTime = (value = new Date()) => {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
};

const newReading = () => ({
  timestamp: localDateTime(),
  temperature: "",
  humidity: "",
  latitude: "",
  longitude: "",
  location_name: "",
  speed: "",
  sensor_id: "manual-observation",
  rfid_id: "",
});

const newScan = () => ({
  event_type: "read",
  timestamp: localDateTime(),
  location_name: "",
  rfid_id: "",
  qr_id: "",
  product_id: "",
  batch_id: "",
  owner: "",
  authorized: "",
});

const newRoutePoint = () => ({
  latitude: "",
  longitude: "",
  location_name: "",
  timestamp: localDateTime(),
});

const numberOrUndefined = (value) => (value === "" ? undefined : Number(value));

export default function AI() {
  const [shipments, setShipments] = useState([]);
  const [shipmentId, setShipmentId] = useState("");
  const [scenario, setScenario] = useState("normal");
  const [readings, setReadings] = useState([newReading()]);
  const [scans, setScans] = useState([newScan()]);
  const [routes, setRoutes] = useState([newRoutePoint()]);
  const [identity, setIdentity] = useState({
    actual_rfid_id: "",
    actual_qr_id: "",
    actual_product_id: "",
    actual_batch_id: "",
    actual_owner: "",
    actual_expiry_date: "",
  });
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [shipmentsLoading, setShipmentsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api.get("/shipments")
      .then(({ data: items }) => {
        if (active) setShipments(items);
      })
      .catch((requestError) => {
        if (active) setError(extractErrorMessage(requestError, "Unable to load shipments."));
      })
      .finally(() => {
        if (active) setShipmentsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const updateReading = (index, key, value) => {
    setReadings((current) => current.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [key]: value } : item));
  };

  const updateScan = (index, key, value) => {
    setScans((current) => current.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [key]: value } : item));
  };

  const updateRoutePoint = (index, key, value) => {
    setRoutes((current) => current.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [key]: value } : item));
  };

  const loadHistory = async (id) => {
    if (!id) {
      setHistory([]);
      return;
    }
    try {
      const response = await api.get(`/ai/shipments/${encodeURIComponent(id)}/history`);
      setHistory(response.data);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to load saved AI analyses."));
    }
  };

  const selectShipment = (id) => {
    setShipmentId(id);
    setData(null);
    setError("");
    setReadings([newReading()]);
    setScans([newScan()]);
    setRoutes([newRoutePoint()]);
    setIdentity({
      actual_rfid_id: "",
      actual_qr_id: "",
      actual_product_id: "",
      actual_batch_id: "",
      actual_owner: "",
      actual_expiry_date: "",
    });
    loadHistory(id);
  };

  const generateScenario = async () => {
    if (!shipmentId) {
      setError("Select a shipment before generating simulator events.");
      return;
    }
    setError("");
    setSimulating(true);
    try {
      const response = await api.post("/ai/simulate", {
        shipment_id: shipmentId,
        scenario,
      });
      const generated = response.data;
      setReadings(generated.readings.map((item) => ({
        ...newReading(),
        ...item,
        timestamp: localDateTime(item.timestamp),
        temperature: item.temperature ?? "",
        humidity: item.humidity ?? "",
        latitude: item.latitude ?? "",
        longitude: item.longitude ?? "",
        speed: item.speed ?? "",
      })));
      setScans(generated.rfid_events.map((item) => ({
        ...newScan(),
        ...item,
        event_type: item.event_type || "read",
        timestamp: localDateTime(item.timestamp),
        authorized: item.authorized === undefined ? "" : String(item.authorized),
      })));
      setIdentity({
        actual_rfid_id: generated.actual_rfid_id || "",
        actual_qr_id: generated.actual_qr_id || "",
        actual_product_id: generated.actual_product_id || "",
        actual_batch_id: generated.actual_batch_id || "",
        actual_owner: generated.actual_owner || "",
        actual_expiry_date: generated.actual_expiry_date || "",
      });
      setRoutes(generated.planned_route.map((item) => ({
        ...newRoutePoint(),
        ...item,
        timestamp: localDateTime(item.timestamp),
      })));
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to generate software simulator events."));
    } finally {
      setSimulating(false);
    }
  };

  const analyze = async (event) => {
    event.preventDefault();
    setError("");
    setData(null);
    setLoading(true);
    const toTimestamp = (value) => (value ? new Date(value).toISOString() : undefined);
    const payload = {
      shipment_id: shipmentId,
      readings: readings.map((item) => ({
        timestamp: toTimestamp(item.timestamp),
        temperature: numberOrUndefined(item.temperature),
        humidity: numberOrUndefined(item.humidity),
        latitude: numberOrUndefined(item.latitude),
        longitude: numberOrUndefined(item.longitude),
        location_name: item.location_name || undefined,
        speed: numberOrUndefined(item.speed),
        sensor_id: item.sensor_id || "manual-observation",
        rfid_id: item.rfid_id || undefined,
      })),
      rfid_events: scans
        .filter((item) => item.location_name.trim())
        .map((item) => ({
          ...item,
          timestamp: toTimestamp(item.timestamp),
          authorized: item.authorized === "" ? undefined : item.authorized === "true",
          rfid_id: item.rfid_id || undefined,
          qr_id: item.qr_id || undefined,
          product_id: item.product_id || undefined,
          batch_id: item.batch_id || undefined,
          owner: item.owner || undefined,
        })),
      planned_route: routes
        .filter((item) => item.latitude !== "" && item.longitude !== "")
        .map((item) => ({
          latitude: Number(item.latitude),
          longitude: Number(item.longitude),
          location_name: item.location_name || "Planned route point",
          timestamp: toTimestamp(item.timestamp),
        })),
      ...Object.fromEntries(
        Object.entries(identity)
          .filter(([key, value]) => key !== "actual_expiry_date" && value.trim())
      ),
      actual_expiry_date: identity.actual_expiry_date || undefined,
    };
    try {
      const response = await api.post("/ai/analyze", payload);
      setData(response.data);
      await loadHistory(shipmentId);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to analyze the submitted observations."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-5">
      <header>
        <h1 className="text-3xl font-bold text-[#102a43]">AI Shipment Analysis</h1>
        <p className="mt-2 text-sm text-slate-600">
          Submit observed telemetry and digital identity scans, or generate events with the software simulator.
          Expected batch values are references only and are never treated as scans.
        </p>
      </header>

      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <form onSubmit={analyze} className="space-y-5">
        <article className="rounded-xl border border-slate-200 bg-white p-5">
          <label htmlFor="ai-shipment" className="block text-sm font-semibold text-slate-700">Shipment</label>
          <select
            id="ai-shipment"
            required
            disabled={shipmentsLoading}
            value={shipmentId}
            onChange={(event) => selectShipment(event.target.value)}
            className="mt-2 w-full max-w-xl rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm"
          >
            <option value="">{shipmentsLoading ? "Loading shipments…" : "Select a shipment"}</option>
            {shipments.map((item) => (
              <option key={item.id} value={item.shipment_id}>
                {item.shipment_id} · {item.status}
              </option>
            ))}
          </select>
          {!shipmentsLoading && shipments.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">No shipments are available for this account.</p>
          )}
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold text-[#102a43]">Software event simulator</h2>
          <p className="mt-1 text-xs text-slate-500">Generated values are explicitly marked as simulated observations. No physical sensors or readers are used.</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <select value={scenario} onChange={(event) => setScenario(event.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
              {SCENARIOS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <button type="button" onClick={generateScenario} disabled={!shipmentId || simulating} className="rounded-lg border border-[#5a1725] px-4 py-2 text-sm font-semibold text-[#5a1725] disabled:opacity-50">
              {simulating ? "Generating…" : "Generate simulator events"}
            </button>
          </div>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold text-[#102a43]">Observed identity values</h2>
          <p className="mt-1 text-xs text-slate-500">Only enter values actually scanned or generated by the simulator. The server independently loads expected values from the shipment’s batch.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["actual_rfid_id", "Observed RFID ID"],
              ["actual_qr_id", "Observed QR ID"],
              ["actual_product_id", "Observed drug/product ID"],
              ["actual_batch_id", "Observed batch ID"],
              ["actual_owner", "Observed owner"],
              ["actual_expiry_date", "Observed expiry date"],
            ].map(([key, label]) => (
              <label key={key} className="text-xs font-medium text-slate-600">
                {label}
                <input
                  type={key === "actual_expiry_date" ? "date" : "text"}
                  value={identity[key]}
                  onChange={(event) => setIdentity((current) => ({ ...current, [key]: event.target.value }))}
                  className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
            ))}
          </div>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-[#102a43]">Environmental and route readings</h2>
            <button type="button" onClick={() => setReadings((current) => [...current, newReading()])} className="text-sm font-semibold text-[#5a1725]">Add reading</button>
          </div>
          <div className="mt-4 space-y-4">
            {readings.map((reading, index) => (
              <div key={`reading-${index}`} className="grid gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  ["timestamp", "Observed at", "datetime-local"],
                  ["temperature", "Temperature °C", "number"],
                  ["humidity", "Humidity %", "number"],
                  ["latitude", "Latitude", "number"],
                  ["longitude", "Longitude", "number"],
                  ["location_name", "Observed location", "text"],
                  ["speed", "Speed", "number"],
                  ["rfid_id", "RFID on reading (optional)", "text"],
                ].map(([key, label, type]) => (
                  <label key={key} className="text-xs font-medium text-slate-600">
                    {label}
                    <input type={type} step={type === "number" ? "any" : undefined} value={reading[key]} onChange={(event) => updateReading(index, key, event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
                  </label>
                ))}
                {readings.length > 1 && <button type="button" onClick={() => setReadings((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-left text-xs text-red-700">Remove reading</button>}
              </div>
            ))}
          </div>
          <div className="mt-6 flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-[#102a43]">Planned route points</h3>
            <button type="button" onClick={() => setRoutes((current) => [...current, newRoutePoint()])} className="text-sm font-semibold text-[#5a1725]">Add route point</button>
          </div>
          <div className="mt-3 space-y-3">
            {routes.map((point, index) => (
              <div key={`route-${index}`} className="grid gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  ["latitude", "Planned route latitude", "number"],
                  ["longitude", "Planned route longitude", "number"],
                  ["location_name", "Planned route location", "text"],
                  ["timestamp", "Planned route time", "datetime-local"],
                ].map(([key, label, type]) => (
                  <label key={key} className="text-xs font-medium text-slate-600">{label}
                    <input type={type} step={type === "number" ? "any" : undefined} value={point[key]} onChange={(event) => updateRoutePoint(index, key, event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                  </label>
                ))}
                {routes.length > 1 && <button type="button" onClick={() => setRoutes((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-left text-xs text-red-700">Remove route point</button>}
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-[#102a43]">Observed QR/RFID scan events</h2>
            <button type="button" onClick={() => setScans((current) => [...current, newScan()])} className="text-sm font-semibold text-[#5a1725]">Add scan event</button>
          </div>
          <p className="mt-1 text-xs text-slate-500">Leave the location empty when no scan was observed.</p>
          <div className="mt-4 space-y-3">
            {scans.map((scan, index) => (
              <div key={`scan-${index}`} className="grid gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-2 lg:grid-cols-4">
                <label className="text-xs font-medium text-slate-600">Observed event type
                  <select value={scan.event_type} onChange={(event) => updateScan(index, "event_type", event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
                    <option value="read">Read</option>
                    <option value="mismatch">Identity mismatch</option>
                    <option value="qr_mismatch">QR mismatch</option>
                    <option value="transfer">Ownership transfer</option>
                  </select>
                </label>
                {[
                  ["timestamp", "Observed at", "datetime-local"],
                  ["location_name", "Scan location", "text"],
                  ["rfid_id", "Scanned RFID ID", "text"],
                  ["qr_id", "Scanned QR ID", "text"],
                  ["product_id", "Observed product ID", "text"],
                  ["batch_id", "Observed batch ID", "text"],
                  ["owner", "Observed owner", "text"],
                ].map(([key, label, type]) => (
                  <label key={key} className="text-xs font-medium text-slate-600">{label}
                    <input type={type} value={scan[key]} onChange={(event) => updateScan(index, key, event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                  </label>
                ))}
                <label className="text-xs font-medium text-slate-600">Transfer authorized?
                  <select value={scan.authorized} onChange={(event) => updateScan(index, "authorized", event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
                    <option value="">Not specified</option>
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                </label>
                {scans.length > 1 && <button type="button" onClick={() => setScans((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-left text-xs text-red-700">Remove scan event</button>}
              </div>
            ))}
          </div>
        </article>

        <button type="submit" disabled={!shipmentId || loading} className="rounded-lg bg-[#5a1725] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
          {loading ? "Analyzing and saving…" : "Analyze and save observations"}
        </button>
      </form>

      {data && (
        <div className="space-y-4">
          <article className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-lg font-semibold text-[#102a43]">Risk score and detected factors</h2>
            <p className="mt-2 text-sm">Score: <strong>{data.risk.score}/100</strong> · {data.risk.risk_level}</p>
            <StructuredData value={{ drivers: data.risk.drivers, factor_evidence: data.risk.factor_evidence, interaction_contributions: data.risk.interaction_contributions }} className="mt-3" />
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-lg font-semibold text-[#102a43]">Identity verification status</h2>
            <StructuredData value={data.counterfeit} className="mt-3" />
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-lg font-semibold text-[#102a43]">Supporting evidence and explanations</h2>
            <StructuredData value={{ explanations: data.explanations, anomalies: data.anomalies, correlations: data.correlations, assessment: data.explainability }} className="mt-3" />
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-lg font-semibold text-[#102a43]">Persistence and ledger status</h2>
            <StructuredData value={{ persistence: data.persistence, fabric: data.blockchain }} className="mt-3" />
          </article>
        </div>
      )}

      {shipmentId && (
        <article className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold text-[#102a43]">Saved analysis history</h2>
          {history.length === 0 ? <p className="mt-2 text-sm text-slate-500">No saved analyses for this shipment.</p> : (
            <ul className="mt-3 space-y-2">
              {history.map((item) => <li key={item.analysis_id} className="rounded-lg bg-slate-50 p-3 text-sm">
                <strong>{item.risk_score}/100 · {item.risk_level}</strong> · {new Date(item.assessed_at).toLocaleString()}
              </li>)}
            </ul>
          )}
        </article>
      )}
    </section>
  );
}
