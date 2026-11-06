import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, KeyRound, ShieldCheck } from "lucide-react";

import { resetPasswordWithLink } from "../services/authService";
import { extractErrorMessage } from "../utils/error";

export default function ResetPassword() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }
    setBusy(true);
    try {
      await resetPasswordWithLink(token, password, confirmPassword);
      navigate("/login", {
        replace: true,
        state: { notice: "Password reset successfully. You can now sign in." },
      });
    } catch (requestError) {
      setError(
        extractErrorMessage(
          requestError,
          "Unable to reset your password. The link may have expired.",
        ),
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
          Choose a new password
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Enter your new password below. It must be at least 8 characters.
        </p>

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block">
            <span className="text-xs font-semibold text-slate-700">New Password</span>
            <input
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Min. 8 characters"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none transition focus:border-[#5a1725]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold text-slate-700">Confirm New Password</span>
            <input
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Repeat new password"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none transition focus:border-[#5a1725]"
            />
          </label>

          <button
            type="submit"
            disabled={busy || !password || !confirmPassword}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:opacity-60"
          >
            <KeyRound size={16} />
            {busy ? "Saving new password..." : "Reset password"}
          </button>
        </form>

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
