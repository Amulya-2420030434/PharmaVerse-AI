import { useState } from "react";
import { Plus } from "lucide-react";
import ApiSchemaForm from "./ApiSchemaForm";

export default function CreateButton({ endpoint, title, label = "Create", initialValues, onSuccess }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#43111c] focus:outline-none focus:ring-2 focus:ring-[#5a1725]/20"
      >
        <Plus size={17} />
        {label}
      </button>

      {open && (
        <ApiSchemaForm
          endpoint={endpoint}
          title={title}
          initialValues={initialValues}
          onClose={() => setOpen(false)}
          onSuccess={onSuccess}
        />
      )}
    </>
  );
}
