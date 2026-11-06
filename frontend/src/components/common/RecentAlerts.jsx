import { ShieldAlert, ChevronRight } from "lucide-react";

function RecentAlerts({ alerts = [], loading = false }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-[#102a43]">Recent AI Alerts</h2>
          <p className="mt-1 text-xs text-slate-500">
            Explainable anomaly assessments
          </p>
        </div>
        <ShieldAlert size={19} className="text-[#5a1725]" />
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-14 animate-pulse rounded-lg bg-slate-100"
            />
          ))}
        </div>
      ) : alerts.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-8 text-center">
          <p className="text-sm font-medium text-slate-600">No stored alerts</p>
          <p className="mt-2 text-xs text-slate-500">
            AI analysis runs on-demand via the AI page. Alerts are not
            persisted between sessions in the current schema.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3"
            >
              <div>
                <p className="text-sm font-medium text-[#102a43]">
                  {alert.title}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {alert.shipment_id}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-red-500/10 px-2 py-1 text-xs text-red-400">
                  {alert.severity}
                </span>
                <ChevronRight size={16} className="text-slate-600" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RecentAlerts;
