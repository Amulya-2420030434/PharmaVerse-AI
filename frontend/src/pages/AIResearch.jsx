import { useEffect, useState } from "react";
import api from "../services/api";
import { extractErrorMessage } from "../utils/error";

function formatTimestamp(value) {
  if (!value) return "Not available";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}

function statusClass(status) {
  if (status === "available") {
    return "text-emerald-700";
  }

  return "text-red-700";
}

function sourceLabel(sourceKey) {
  const labels = {
    ndc: "FDA NDC Directory",
    shortages: "FDA Drug Shortages",
    enforcement: "FDA Drug Enforcement",
  };

  return labels[sourceKey] || sourceKey;
}

export default function AIResearch() {
  const [status, setStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [fdaLive, setFdaLive] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    Promise.all([
      api.get("/ml/status"),
      api.get("/ml/metrics"),
      api.get("/ai/fda-live/summary"),
    ])
      .then(([statusResponse, metricsResponse, fdaResponse]) => {
        if (!active) return;

        setStatus(statusResponse.data);
        setMetrics(metricsResponse.data);
        setFdaLive(fdaResponse.data);
      })
      .catch((requestError) => {
        if (active) {
          setError(
            extractErrorMessage(
              requestError,
              "Unable to load AI research information.",
            ),
          );
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section>
      <h1 className="text-3xl font-bold text-[#102a43]">AI Research</h1>

      <p className="mt-2 text-sm text-slate-600">
        Operational AI remains deterministic. This view exposes the measured
        ML artifact and current external FDA pharmaceutical intelligence.
      </p>

      {error && (
        <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Model status
          </h2>

          <p
            className={`mt-3 text-xl font-bold ${
              status?.available ? "text-emerald-700" : "text-slate-700"
            }`}
          >
            {status
              ? status.available
                ? "Available"
                : "Unavailable"
              : "Loading…"}
          </p>

          <p className="mt-2 text-sm text-slate-600">
            {status?.reason || "Checking configured artifact."}
          </p>

          {status?.artifact && (
            <p className="mt-2 break-all text-xs text-slate-500">
              {status.artifact}
            </p>
          )}
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Evaluation metrics
          </h2>

          {metrics?.metrics &&
          Object.keys(metrics.metrics).length ? (
            <dl className="mt-3 grid grid-cols-2 gap-3">
              {Object.entries(metrics.metrics).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs text-slate-500">{key}</dt>
                  <dd className="text-lg font-semibold text-[#102a43]">
                    {typeof value === "number"
                      ? value.toFixed(3)
                      : String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="mt-3 text-sm text-slate-600">
              No trained artifact metrics available.
            </p>
          )}
        </article>
      </div>

      <article className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-2 md:flex-row md:items-center">
          <div>
            <h2 className="text-lg font-bold text-[#102a43]">
              External FDA Reference Status
            </h2>

            <p className="mt-1 text-sm text-slate-600">
              FDA/openFDA requests are live or near-current. Data freshness
              varies by source (enforcement updates weekly) and remains
              separate from the TRACE-X-Bench ML training dataset.
            </p>
          </div>

          {fdaLive?.checked_at && (
            <p className="text-xs text-slate-500">
              Checked: {formatTimestamp(fdaLive.checked_at)}
            </p>
          )}
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {["ndc", "shortages", "enforcement"].map((sourceKey) => {
            const source = fdaLive?.sources?.[sourceKey];

            return (
              <div
                key={sourceKey}
                className="rounded-lg border border-slate-200 p-4"
              >
                <h3 className="font-semibold text-[#102a43]">
                  {sourceLabel(sourceKey)}
                </h3>

                <p
                  className={`mt-2 text-sm font-semibold ${statusClass(
                    source?.status,
                  )}`}
                >
                  {source
                    ? source.status === "available"
                      ? "Available"
                      : "Unavailable"
                    : "Loading…"}
                </p>

                {source && (
                  <>
                    <dl className="mt-3 space-y-2 text-sm">
                      <div>
                        <dt className="text-slate-500">Source freshness</dt>
                        <dd className="font-medium text-slate-800">
                          {source.freshness}
                        </dd>
                      </div>

                      <div>
                        <dt className="text-slate-500">Records</dt>
                        <dd className="font-medium text-slate-800">
                          {source.count ?? "Unavailable"}
                        </dd>
                      </div>

                      <div>
                        <dt className="text-slate-500">Retrieved</dt>
                        <dd className="font-medium text-slate-800">
                          {formatTimestamp(source.retrieved_at)}
                        </dd>
                      </div>

                      <div>
                        <dt className="text-slate-500">Cache</dt>
                        <dd className="font-medium text-slate-800">
                          {source.cached ? "Cached" : "Live fetch"}
                        </dd>
                      </div>
                    </dl>

                    {source.error && (
                      <p className="mt-3 text-xs text-red-600">
                        {source.error}
                      </p>
                    )}

                    <a
                      href={source.source_endpoint}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-4 inline-block text-xs font-medium text-blue-700 hover:underline"
                    >
                      Open source endpoint
                    </a>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </article>

      <p className="mt-5 text-xs text-slate-500">
        TRACE-X-Bench is the static synthetic benchmark used for ML
        training/evaluation. FDA data is external reference and supply-risk
        context and is not automatically used as ML input.
      </p>
    </section>
  );
}