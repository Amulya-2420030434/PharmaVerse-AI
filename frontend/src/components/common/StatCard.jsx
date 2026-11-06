import {
  Pill,
  Truck,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Blocks,
  Activity,
  Brain
} from "lucide-react";

const icons = {
  drugs: Pill,
  shipments: Truck,
  verified: ShieldCheck,
  counterfeits: ShieldAlert,
  anomalies: AlertTriangle,
  blockchain: Blocks,
  iot: Activity,
  ai: Brain
};

function StatCard({
  title,
  value = "—",
  description,
  icon = "drugs",
  status = "neutral"
}) {
  const Icon = icons[icon] || Pill;

  const statusClasses = {
    neutral: "text-slate-600 bg-slate-100",
    success: "text-emerald-700 bg-emerald-50",
    warning: "text-amber-700 bg-amber-50",
    danger: "text-red-700 bg-red-50",
    info: "text-[#1f4e79] bg-blue-50"
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between">

        <div>
          <p className="text-sm font-medium text-slate-600">
            {title}
          </p>

          <p className="mt-2 text-3xl font-bold text-[#102a43]">
            {value}
          </p>
        </div>

        <div
          className={`rounded-lg p-2.5 ${statusClasses[status]}`}
        >
          <Icon size={20} />
        </div>

      </div>

      {description && (
        <p className="mt-4 text-xs text-slate-500">
          {description}
        </p>
      )}
    </div>
  );
}

export default StatCard;