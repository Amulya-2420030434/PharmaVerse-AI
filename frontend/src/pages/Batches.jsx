import { useNavigate } from "react-router-dom";
import ApiResourceTable from "../components/common/ApiResourceTable";
import CreateButton from "../components/common/CreateButton";
import { useState } from "react";

export default function Batches() {
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <section>
      <div className="mb-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">API data</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">Batch Management</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Review active pharmaceutical batches, expiry dates, quantities, and ledger identifiers.</p>
        </div>
        <CreateButton endpoint="/batches" title="Create Batch" onSuccess={() => setRefreshKey((value) => value + 1)} />
      </div>
      <div key={refreshKey}>
        <ApiResourceTable
          title="Batch Management"
          description=""
          showIntro={false}
          endpoint="/batches"
          searchKeys={["batch_id", "drug_id", "status"]}
          getRowId={(item) => item.batch_id}
          onRowClick={(item) => navigate(`/audit?batch_id=${encodeURIComponent(item.batch_id)}`)}
          columns={[
            { key: "batch_id", label: "Batch ID" },
            { key: "drug_id", label: "Drug ID" },
            { key: "manufacturing_date", label: "Manufactured" },
            { key: "expiry_date", label: "Expires" },
            { key: "quantity", label: "Quantity" },
            { key: "status", label: "Status" },
          ]}
        />
      </div>
    </section>
  );
}
