function labelFor(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function valueText(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function Value({ value, depth }) {
  if (Array.isArray(value)) {
    if (!value.length) return <span className="text-slate-500">No records</span>;
    return (
      <ul className="space-y-3">
        {value.map((item, index) => (
          <li key={item?.id || item?.shipment_id || item?.alert_type || index} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <Value value={item} depth={depth + 1} />
          </li>
        ))}
      </ul>
    );
  }
  if (value && typeof value === "object") {
    if (depth > 5) return <span className="text-slate-500">Nested details omitted</span>;
    const entries = Object.entries(value);
    if (!entries.length) return <span className="text-slate-500">No details</span>;
    return (
      <dl className="grid gap-3 sm:grid-cols-2">
        {entries.map(([key, item]) => (
          <div key={key} className="min-w-0">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{labelFor(key)}</dt>
            <dd className="mt-1 break-words text-sm text-slate-800"><Value value={item} depth={depth + 1} /></dd>
          </div>
        ))}
      </dl>
    );
  }
  return <span>{valueText(value)}</span>;
}

export default function StructuredData({ value, className = "" }) {
  return <div className={className}><Value value={value} depth={0} /></div>;
}
