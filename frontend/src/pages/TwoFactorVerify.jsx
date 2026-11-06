import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, KeyRound, ShieldCheck } from "lucide-react";

import { verifyTwoFactor } from "../services/authService";
import { extractErrorMessage } from "../utils/error";

export default function TwoFactorVerify() {
  const location = useLocation();
  const navigate = useNavigate();
  const email = location.state?.email || "";
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!email) return <Navigate to="/login" replace />;

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await verifyTwoFactor(email, otp);
      navigate("/dashboard", { replace: true });
    } catch (requestError) {
      setError(
        extractErrorMessage(
          requestError,
          "Invalid or expired verification code.",
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
          Two-factor verification
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Enter the 6-digit verification code sent to <strong>{email}</strong>.
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
            <span className="text-xs font-semibold text-slate-700">
              6-Digit Verification Code
            </span>
            <input
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              minLength={6}
              maxLength={6}
              required
              value={otp}
              onChange={(event) =>
                setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
              placeholder="123456"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-center font-mono text-base tracking-widest text-[#102a43] outline-none transition focus:border-[#5a1725]"
            />
          </label>

          <button
            type="submit"
            disabled={busy || otp.length < 6}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:opacity-60"
          >
            <KeyRound size={16} />
            {busy ? "Verifying code..." : "Verify & Enter Dashboard"}
          </button>
        </form>

        <div className="mt-6 border-t border-slate-100 pt-4 text-center">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft size={14} /> Back to Sign In
          </Link>
        </div>
      </section>
    </main>
  );
}
