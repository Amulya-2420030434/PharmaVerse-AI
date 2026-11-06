function DashboardHeader({ loading = false, error = "" }) {
  const indicator = error
    ? { dot: "bg-red-500", badge: "border-red-200 bg-red-50", text: "text-red-800", label: "Error loading data" }
    : loading
      ? { dot: "bg-amber-400 animate-pulse", badge: "border-amber-200 bg-amber-50", text: "text-amber-800", label: "Loading…" }
      : { dot: "bg-emerald-500", badge: "border-emerald-200 bg-emerald-50", text: "text-emerald-800", label: "Live data" };

  return (
    <div className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">
          PharmaVerse AI
        </p>

        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">
          Supply Chain Dashboard
        </h1>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Monitor pharmaceutical traceability, shipments, anomalies, and
          verification status across your supply chain.
        </p>
      </div>

      <div
        className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${indicator.badge}`}
      >
        <span className={`h-2 w-2 rounded-full ${indicator.dot}`} />
        <span className={`text-xs font-medium ${indicator.text}`}>
          {indicator.label}
        </span>
      </div>
    </div>
  );
}

export default DashboardHeader;
