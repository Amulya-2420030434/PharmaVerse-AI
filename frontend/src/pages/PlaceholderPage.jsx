import { CircleDashed } from "lucide-react";

function PlaceholderPage({ title, description }) {
  return (
    <section>

      <div className="mb-8">

        <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">
          PharmaVerse AI
        </p>

        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">
          {title}
        </h1>

        <p className="mt-2 max-w-2xl text-slate-600">
          {description}
        </p>

      </div>

      <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center shadow-sm">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100">
          <CircleDashed size={24} className="text-[#1f4e79]" />
        </div>

        <p className="mt-4 text-base font-semibold text-[#102a43]">
          Backend integration pending
        </p>

        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
          This module is ready for its service integration and will not display
          operational data until the relevant backend is connected.
        </p>

      </div>

    </section>
  );
}

export default PlaceholderPage;