import {
  Database,
  Brain,
  Blocks,
  Radio
} from "lucide-react";

// Maps the service names returned by the backend to their icon components.
const SERVICE_ICONS = {
  "Application API": Radio,
  "PostgreSQL": Database,
  "Hyperledger Fabric": Blocks,
  "Fabric Gateway": Blocks,
  "AI Engine": Brain,
};

// Visual style for each status value reported by the backend.
const STATUS_STYLES = {
  operational: { dot: "bg-emerald-500", label: "Operational", text: "text-emerald-700" },
  disabled:    { dot: "bg-slate-400",   label: "Disabled",    text: "text-slate-500"   },
  unavailable: { dot: "bg-red-500",     label: "Unavailable", text: "text-red-600"     },
};

function ServiceRow({ name, status, detail }) {
  const Icon = SERVICE_ICONS[name] ?? Radio;
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.unavailable;

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-blue-50 p-2">
          <Icon size={17} className="text-[#1f4e79]" />
        </div>
        <div>
          <span className="text-sm font-medium text-slate-700">{name}</span>
          {detail && (
            <p className="mt-0.5 max-w-xs truncate text-xs text-slate-400" title={detail}>
              {detail}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${style.dot}`} />
        <span className={`text-xs font-medium ${style.text}`}>
          {style.label}
        </span>
      </div>
    </div>
  );
}

function LoadingRow() {
  return (
    <div className="flex items-center justify-between animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-slate-100" />
        <div className="h-4 w-32 rounded bg-slate-100" />
      </div>
      <div className="h-4 w-20 rounded bg-slate-100" />
    </div>
  );
}

function SystemStatus({ status = null, loading = false }) {
  // Build an ordered list of services from the backend response object.
  // IoT status is retained by the backend response for legacy compatibility;
  // it is outside the supported UI scope.
  const services = status
    ? [
        status.api,
        status.database,
        status.blockchain,
        status.ai_engine,
      ].filter(Boolean)
    : [];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="font-semibold text-[#102a43]">System Status</h2>
        <p className="mt-1 text-xs text-slate-500">
          {loading
            ? "Checking service health…"
            : status
              ? "Current health of each platform component."
              : "Service health unavailable."}
        </p>
      </div>

      <div className="space-y-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <LoadingRow key={i} />)
          : services.map((svc) => (
              <ServiceRow
                key={svc.name}
                name={svc.name}
                status={svc.status}
                detail={svc.detail}
              />
            ))}
      </div>
    </div>
  );
}

export default SystemStatus;
