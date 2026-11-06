import { Clock3 } from "lucide-react";

function RecentActivity({ events = [], loading = false }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="font-semibold text-[#102a43]">Supply Chain Activity</h2>
        <p className="mt-1 text-xs text-slate-500">Recent traceability events</p>
      </div>

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-3 animate-pulse">
              <div className="mt-1 h-2 w-2 rounded-full bg-slate-200" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-3/4 rounded bg-slate-100" />
                <div className="h-3 w-1/3 rounded bg-slate-100" />
              </div>
            </div>
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-8 text-center">
          <Clock3 size={20} className="mx-auto text-slate-400" />
          <p className="mt-3 text-sm font-medium text-slate-600">
            No activity yet
          </p>
          <p className="mt-2 text-xs text-slate-500">
            Supply chain events will appear here once shipments are created.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {events.map((event) => (
            <div key={event.id} className="flex gap-3">
              <div className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-[#5a1725]" />
              <div>
                <p className="text-sm text-slate-700">{event.description}</p>
                <p className="mt-1 text-xs text-slate-500">{event.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RecentActivity;
