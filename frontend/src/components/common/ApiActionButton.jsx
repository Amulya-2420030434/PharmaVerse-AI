import { useState } from "react";
import { Play } from "lucide-react";
import ApiSchemaForm from "./ApiSchemaForm";

export default function ApiActionButton({ endpoint, title, label, onSuccess, initialValues = {} }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-[#5a1725] hover:text-[#5a1725]"
      >
        <Play size={15} />
        {label}
      </button>
      {open && (
        <ApiSchemaForm
          endpoint={endpoint}
          title={title}
          submitLabel={label}
          initialValues={initialValues}
          onClose={() => setOpen(false)}
          onSuccess={onSuccess}
        />
      )}
    </>
  );
}
