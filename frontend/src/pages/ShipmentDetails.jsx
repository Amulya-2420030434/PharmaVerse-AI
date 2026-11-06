/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Circle, MapPin, PackageCheck, Truck } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import ApiActionButton from "../components/common/ApiActionButton";
import api from "../services/api";
import { getStoredUser } from "../services/authService";
import { extractErrorMessage } from "../utils/error";

function parseDate(value, naiveIsUtc = false) {
  if (!value) return null;
  const normalized = naiveIsUtc && typeof value === "string" && !/[zZ]|[+-]\d{2}:\d{2}$/.test(value)
    ? `${value}Z`
    : value;
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDate(value, naiveIsUtc = false) {
  if (!value) return null;
  const parsed = parseDate(value, naiveIsUtc);
  return parsed ? parsed.toLocaleString() : String(value);
}

const EMPTY_EVENTS = [];

function TimelineStep({ title, location, detail, time, timeLabel, expected, state, icon: Icon }) {
  const complete = state === "complete";
  const current = state === "current";
  return (
    <li className="relative flex gap-4 pb-8 last:pb-0">
      <div className={`relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 ${complete ? "border-emerald-600 bg-emerald-600 text-white" : current ? "border-[#5a1725] bg-rose-50 text-[#5a1725]" : "border-slate-200 bg-white text-slate-400"}`}>
        {complete ? <Check size={18} /> : Icon ? <Icon size={18} /> : <Circle size={12} />}
      </div>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className={`font-semibold ${complete || current ? "text-[#102a43]" : "text-slate-500"}`}>{title}</h3>
          {current && <span className="rounded-full bg-rose-50 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-[#5a1725]">Current</span>}
        </div>
        {location && <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-600"><MapPin size={14} />{location}</p>}
        {detail && <p className="mt-1 text-sm text-slate-500">{detail}</p>}
        {(time || expected) && (
          <p className="mt-2 text-xs text-slate-500">
            {time ? `${timeLabel || "Actual"}: ${formatDate(time, true)}` : `Expected: ${formatDate(expected)}`}
            {time && expected && parseDate(time, true) > parseDate(expected) && (
              <span className="ml-2 font-semibold text-amber-700">Later than expected</span>
            )}
            {time && expected && parseDate(time, true) <= parseDate(expected) && (
              <span className="ml-2">Expected: {formatDate(expected)}</span>
            )}
          </p>
        )}
        {!time && !expected && state === "upcoming" && <p className="mt-2 text-xs text-slate-400">Upcoming</p>}
        {!time && expected && state === "upcoming" && parseDate(expected) < new Date() && (
          <p className="mt-2 text-xs font-semibold text-amber-700">Past expected time</p>
        )}
      </div>
    </li>
  );
}

function shipmentSteps(shipment, events) {
  const created = events.find((event) => event.event_type === "CREATED");
  const departed = events.find((event) => event.event_type === "DEPARTED");
  const delivered = events.find((event) => event.event_type === "DELIVERED");
  const inTransit = shipment.status === "IN_TRANSIT";
  const isDelivered = shipment.status === "DELIVERED";
  const additionalEvents = events.filter((event) =>
    ["CHECKPOINT", "TRANSFERRED"].includes(event.event_type),
  );
  return [
    {
      key: "created",
      title: "Shipment created",
      location: shipment.source,
      time: created?.event_time || shipment.created_at,
      expected: null,
      state: "complete",
      icon: PackageCheck,
    },
    {
      key: "departed",
      title: "Departed from source",
      location: shipment.source,
      time: departed?.event_time || shipment.actual_departure,
      expected: shipment.expected_departure,
      state: shipment.actual_departure || departed ? "complete" : "upcoming",
      icon: Truck,
    },
    {
      key: "in-transit",
      title: "In transit",
      location: inTransit
        ? "Live location is not available"
        : isDelivered
          ? null
          : null,
      detail: inTransit
        ? "No persisted live location or checkpoint is available for this shipment."
        : null,
      time: departed?.event_time || shipment.actual_departure,
      timeLabel: "In transit since",
      expected: null,
      state: inTransit ? "current" : isDelivered ? "complete" : "upcoming",
      icon: Truck,
    },
    ...additionalEvents.map((event) => ({
      key: event.id,
      title: event.event_type === "CHECKPOINT" ? "Route checkpoint" : "Custody transferred",
      location: event.location_name,
      detail: event.description,
      time: event.event_time,
      expected: event.expected_time,
      state: "complete",
      icon: MapPin,
    })),
    {
      key: "delivered",
      title: "Arrived at destination · Delivered",
      location: shipment.destination,
      detail: isDelivered ? delivered?.description : "Arrival is recorded when the shipment is received.",
      time: delivered?.event_time || shipment.actual_arrival,
      expected: shipment.expected_arrival,
      state: isDelivered ? "complete" : "upcoming",
      icon: MapPin,
    },
  ];
}

export default function ShipmentDetails() {
  const { id } = useParams();
  const [shipment, setShipment] = useState(null);
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState("");
  const [trackingError, setTrackingError] = useState("");
  const [loading, setLoading] = useState(true);
  const user = getStoredUser();

  const loadShipment = useCallback(async () => {
    setLoading(true);
    setError("");
    setTrackingError("");
    try {
      const response = await api.get(`/shipments/${encodeURIComponent(id)}`);
      setShipment(response.data);
      try {
        const trackingResponse = await api.get(`/shipments/${encodeURIComponent(id)}/tracking`);
        setTracking(trackingResponse.data);
      } catch (trackingRequestError) {
        setTracking(null);
        setTrackingError(extractErrorMessage(trackingRequestError, "Unable to load persisted tracking events."));
      }
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to load shipment."));
      setShipment(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadShipment();
  }, [loadShipment]);

  const actionEndpoint = (action) => `/shipments/${encodeURIComponent(id)}/${action}`;
  const canDepart = ["ADMIN", "MANUFACTURER", "DISTRIBUTOR", "TRANSPORTER"].includes(user?.role);
  const canReceive = ["ADMIN", "DISTRIBUTOR", "PHARMACY"].includes(user?.role);
  const ownerNames = [user?.organization, user?.username].filter(Boolean).map((name) => name.toLowerCase());
  const canTransfer = user?.role === "ADMIN" || (
    ["MANUFACTURER", "DISTRIBUTOR", "PHARMACY"].includes(user?.role) &&
    ownerNames.includes((shipment?.current_owner || "").trim().toLowerCase())
  );
  const events = tracking?.events ?? EMPTY_EVENTS;
  const steps = useMemo(
    () => shipment ? shipmentSteps(shipment, events) : [],
    [shipment, events],
  );
  const progress = shipment?.status === "DELIVERED" ? 100 : shipment?.status === "IN_TRANSIT" ? 75 : 25;
  const currentLocation = shipment?.status === "DELIVERED"
    ? shipment.destination
    : shipment?.status === "CREATED"
      ? shipment.source
      : shipment?.current_latitude != null && shipment?.current_longitude != null
        ? `${shipment.current_latitude}, ${shipment.current_longitude} (coordinates)`
        : "No live location reported";

  return (
    <section>
      <Link to="/shipments" className="text-sm font-medium text-[#5a1725]">← Back to shipments</Link>
      {loading && <div className="mt-5 rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading shipment and tracking…</div>}
      {error && <div role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {shipment && (
        <>
          <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">Delivery tracking</p>
              <h1 className="mt-2 text-3xl font-bold text-[#102a43]">{shipment.shipment_id}</h1>
              <p className="mt-2 text-sm text-slate-600">Batch {tracking?.batch_id || "Public batch ID unavailable"}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {canDepart && shipment.status === "CREATED" && <ApiActionButton endpoint={actionEndpoint("depart")} title="Depart Shipment" label="Depart" onSuccess={loadShipment} />}
              {canReceive && shipment.status === "IN_TRANSIT" && <ApiActionButton endpoint={actionEndpoint("receive")} title="Receive Shipment" label="Receive" onSuccess={loadShipment} />}
              {canTransfer && <ApiActionButton endpoint={actionEndpoint("transfer")} title="Transfer Shipment" label="Transfer" initialValues={{ new_owner: "" }} onSuccess={loadShipment} />}
            </div>
          </div>

          <article className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Current status</p>
                <p className="mt-1 text-2xl font-bold text-[#102a43]">{shipment.status.replaceAll("_", " ")}</p>
              </div>
              <div className="text-sm sm:text-right">
                <p className="font-semibold text-slate-700">Current location</p>
                <p className="mt-1 text-slate-600">{currentLocation}</p>
              </div>
            </div>
            <div className="mt-5">
              <div className="mb-2 flex justify-between text-xs text-slate-500"><span>Lifecycle milestones</span><span>{progress}%</span></div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-600 transition-all" style={{ width: `${progress}%` }} /></div>
              <div className="mt-2 flex justify-between text-xs text-slate-500"><span>{shipment.source}</span><span>{shipment.destination}</span></div>
            </div>
          </article>

          {trackingError && <div role="alert" className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{trackingError}</div>}
          <div className="mt-6 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-semibold text-[#102a43]">Shipment timeline</h2>
              <p className="mt-1 text-sm text-slate-500">Only recorded lifecycle events and timestamps are shown. No route stops are inferred.</p>
              <div className="relative mt-6">
                <div className="absolute bottom-4 left-5 top-4 w-px bg-slate-200" />
                <ol className="relative">
                  {steps.map(({ key, ...step }) => <TimelineStep key={key} {...step} />)}
                </ol>
              </div>
            </article>
            <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-semibold text-[#102a43]">Shipment details</h2>
              <dl className="mt-4 divide-y divide-slate-100">
                {[
                  ["Batch ID", tracking?.batch_id || "Unavailable"],
                  ["Source", shipment.source],
                  ["Destination", shipment.destination],
                  ["Current owner", shipment.current_owner || "Not recorded"],
                  ["Expected departure", formatDate(shipment.expected_departure) || "Not scheduled"],
                  ["Actual departure", formatDate(shipment.actual_departure, true) || "Not recorded"],
                  ["Expected arrival", formatDate(shipment.expected_arrival) || "Not scheduled"],
                  ["Actual arrival", formatDate(shipment.actual_arrival, true) || "Not recorded"],
                ].map(([label, value]) => (
                  <div key={label} className="grid gap-1 py-3 sm:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</dt>
                    <dd className="break-words text-sm text-slate-700">{value}</dd>
                  </div>
                ))}
              </dl>
            </article>
          </div>
        </>
      )}
    </section>
  );
}
