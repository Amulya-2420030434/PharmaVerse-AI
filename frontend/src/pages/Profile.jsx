import { useEffect, useState } from "react";
import { getCurrentUser } from "../services/authService";
import { extractErrorMessage } from "../utils/error";

export default function Profile() {
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCurrentUser().then(setUser).catch((requestError) => setError(extractErrorMessage(requestError, "Unable to load your profile."))).finally(() => setLoading(false));
  }, []);

  return (
    <section>
      <h1 className="text-3xl font-bold text-[#102a43]">Profile</h1>
      {error && <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {loading && <p role="status" className="mt-5 text-sm text-slate-500">Loading profile…</p>}
      {user && (
        <div className="mt-6 grid max-w-2xl gap-4 rounded-xl border border-slate-200 bg-white p-6 sm:grid-cols-2">
          {Object.entries(user).map(([key, value]) => (
            <div key={key} className="border-b border-slate-100 py-3">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">{key.replaceAll("_", " ")}</div>
              <div className="mt-1 text-sm text-slate-700">{value === null || value === "" ? "—" : String(value)}</div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
