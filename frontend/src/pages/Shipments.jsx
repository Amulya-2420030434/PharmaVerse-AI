import { useNavigate } from "react-router-dom";
import { useState } from "react";
import ApiResourceTable from "../components/common/ApiResourceTable";
import CreateButton from "../components/common/CreateButton";

export default function Shipments() {
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <section>
      <div className="mb-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">API data</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">Shipment Monitoring</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Track shipment ownership, route endpoints, delivery state, and expected arrival.</p>
        </div>
        <CreateButton endpoint="/shipments" title="Create Shipment" onSuccess={() => setRefreshKey((value) => value + 1)} />
      </div>
      <div key={refreshKey}>
        <ApiResourceTable
          title="Shipment Monitoring"
          description=""
          showIntro={false}
          endpoint="/shipments"
          searchKeys={["shipment_id", "source", "destination", "current_owner", "status"]}
          getRowId={(item) => item.shipment_id}
          onRowClick={(item) => navigate(`/shipments/${encodeURIComponent(item.shipment_id)}`)}
          columns={[
            { key: "shipment_id", label: "Shipment ID" },
            { key: "source", label: "Source" },
            { key: "destination", label: "Destination" },
            { key: "current_owner", label: "Owner" },
            { key: "status", label: "Status" },
            { key: "expected_arrival", label: "Expected arrival" },
          ]}
        />
      </div>
    </section>
  );
}
