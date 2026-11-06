import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

function ShipmentChart({ data = [], loading = false }) {
  const hasData = data.length > 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="font-semibold text-[#102a43]">Shipment Status</h2>
        <p className="mt-1 text-xs text-slate-500">
          Current pharmaceutical shipment lifecycle
        </p>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center rounded-lg bg-slate-50 animate-pulse">
          <p className="text-sm text-slate-400">Loading…</p>
        </div>
      ) : !hasData ? (
        <div className="flex h-64 items-center justify-center rounded-lg bg-slate-50">
          <div className="text-center">
            <p className="text-sm font-medium text-slate-600">
              No shipment data yet
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Create shipments to see their status breakdown here.
            </p>
          </div>
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "#ffffff",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey="value" fill="#5a1725" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default ShipmentChart;
