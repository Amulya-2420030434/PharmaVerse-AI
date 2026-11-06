import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Mail, ShieldCheck } from "lucide-react";

import { forgotPassword } from "../services/authService";
import { extractErrorMessage } from "../utils/error";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (requestError) {
      setError(
        extractErrorMessage(requestError, "Unable to request a password reset."),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f7f8fa] px-4 py-8 text-[#102a43]">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-lg sm:p-8">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#5a1725] text-white">
          <ShieldCheck size={22} />
        </div>

        <p className="mt-5 text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">
          PharmaVerse AI Security
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-[#102a43]">
          Reset your password
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Enter your registered email address and we will send you secure password reset instructions.
        </p>

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        {sent ? (
          <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-center">
            <CheckCircle2 className="mx-auto text-emerald-600" size={36} />
            <p className="mt-3 text-sm font-semibold text-emerald-900">
              Reset instructions sent!
            </p>
            <p className="mt-1 text-xs text-emerald-800">
              If an account exists for {email}, a secure password reset email has been dispatched.
            </p>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block">
              <span className="text-xs font-semibold text-slate-700">Account Email</span>
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@organization.com"
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none transition focus:border-[#5a1725]"
              />
            </label>

            <button
              type="submit"
              disabled={busy || !email}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:opacity-60"
            >
              <Mail size={16} />
              {busy ? "Sending instructions..." : "Send password reset instructions"}
            </button>
          </form>
        )}

        <div className="mt-6 border-t border-slate-100 pt-4 text-center">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft size={14} /> Return to sign in
          </Link>
        </div>
      </section>
    </main>
  );
}
