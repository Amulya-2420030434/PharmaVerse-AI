import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, ShieldCheck } from "lucide-react";

import { confirmEmailVerification } from "../services/authService";
import { extractErrorMessage } from "../utils/error";

export default function VerifyEmail() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const verify = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await confirmEmailVerification(token);
      sessionStorage.setItem("registration_verification_token", result.verification_token);
      sessionStorage.setItem("registration_email", result.email);
      navigate("/register", {
        replace: true,
        state: {
          verificationToken: result.verification_token,
          email: result.email,
        },
      });
    } catch (requestError) {
      setError(
        extractErrorMessage(
          requestError,
          "This verification link is invalid or expired.",
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
          Verify your email
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Confirm this one-time link to continue creating your account.
        </p>

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        <button
          type="button"
          disabled={busy}
          onClick={verify}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:opacity-60"
        >
          <CheckCircle2 size={16} />
          {busy ? "Verifying..." : "Verify email and continue"}
        </button>

        <div className="mt-6 border-t border-slate-100 pt-4 text-center">
          <Link
            to="/register"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft size={14} /> Request a new link
          </Link>
        </div>
      </section>
    </main>
  );
}
