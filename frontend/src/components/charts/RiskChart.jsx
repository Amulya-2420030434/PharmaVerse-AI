import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from "recharts";

function RiskChart({ data = [], loading = false }) {
  const hasData = data.some((item) => item.value > 0);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="font-semibold text-[#102a43]">Operational status indicators</h2>
        <p className="mt-1 text-xs text-slate-500">
          Derived from batch status, expiry, and overdue shipments—not an AI risk score.
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
              No operational status data yet
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Add batches and shipments to see the risk breakdown.
            </p>
          </div>
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={75}
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#ffffff",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                }}
              />
              <Legend
                iconType="circle"
                iconSize={10}
                wrapperStyle={{ fontSize: "12px" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default RiskChart;
