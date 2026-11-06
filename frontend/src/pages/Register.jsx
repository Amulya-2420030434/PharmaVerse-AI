import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  ArrowLeft,
  Clock,
  Info,
  Mail,
  ShieldCheck,
  UserCheck,
} from "lucide-react";

import {
  registerEmail,
  registerGoogle,
  sendOtp,
  verifyGoogleToken,
  verifyOtp,
} from "../services/authService";
import { extractErrorMessage } from "../utils/error";

const ALLOWED_ROLES = [
  { value: "PHARMACY", label: "Pharmacy / Healthcare Provider" },
  { value: "MANUFACTURER", label: "Drug Manufacturer" },
  { value: "DISTRIBUTOR", label: "Wholesale Distributor" },
  { value: "TRANSPORTER", label: "Logistics & Transport Carrier" },
];

function GoogleIcon() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      />
    </svg>
  );
}

export default function Register() {
  const location = useLocation();

  const [method, setMethod] = useState(
    location.state?.googleRegToken || location.state?.method === "google"
      ? "google"
      : "email",
  );
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [submissionMessage, setSubmissionMessage] = useState("");

  // Option 1: Email state
  const [emailStep, setEmailStep] = useState(1); // 1: Email, 2: OTP, 3: Profile Details
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [verificationToken, setVerificationToken] = useState("");
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [organization, setOrganization] = useState("");
  const [requestedRole, setRequestedRole] = useState("PHARMACY");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Option 2: Google state
  const [googleStep, setGoogleStep] = useState(
    location.state?.googleRegToken ? 2 : 1,
  );
  const [googleEmail, setGoogleEmail] = useState(
    location.state?.googleEmail || "",
  );
  const [googleName, setGoogleName] = useState(
    location.state?.googleName || "",
  );
  const [googleRegToken, setGoogleRegToken] = useState(
    location.state?.googleRegToken || "",
  );
  const [googleUsername, setGoogleUsername] = useState(
    location.state?.googleEmail
      ? location.state.googleEmail.split("@")[0].replace(/[^a-zA-Z0-9_]/g, "").slice(0, 50)
      : "",
  );
  const [googleOrg, setGoogleOrg] = useState("");
  const [googleRole, setGoogleRole] = useState("PHARMACY");
  const [googlePassword, setGooglePassword] = useState("");

  // Shared UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const registerGoogleButtonRef = useRef(null);
  const hasRegisterRenderedRef = useRef(false);
  const [googleReady, setGoogleReady] = useState(false);

  const processGoogleToken = useCallback(async (idToken) => {
    setLoading(true);
    setError("");
    try {
      const res = await verifyGoogleToken(idToken);
      if (res.existing_user) {
        if (res.auth_provider === "local" || !res.auth_provider) {
          setError(
            `An account with this email address already exists using email and password. Please sign in using your email and password.`,
          );
        } else {
          setError(
            `An account with this Google account already exists (Status: ${res.status}). Please sign in using Google.`,
          );
        }
        return;
      }
      setGoogleEmail(res.email);
      setGoogleName(res.name);
      setGoogleRegToken(res.registration_token);
      setGoogleUsername(
        res.email.split("@")[0].replace(/[^a-zA-Z0-9_]/g, "").slice(0, 50),
      );
      setGoogleStep(2);
    } catch (err) {
      setError(extractErrorMessage(err, "Google identity verification failed."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!googleClientId || method !== "google" || googleStep !== 1) return;

    let isMounted = true;
    const setupGoogle = () => {
      if (
        !hasRegisterRenderedRef.current &&
        window.google?.accounts?.id &&
        registerGoogleButtonRef.current &&
        isMounted
      ) {
        try {
          window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: (response) => {
              if (response?.credential) {
                processGoogleToken(response.credential);
              }
            },
            auto_select: false,
            cancel_on_tap_outside: true,
          });

          registerGoogleButtonRef.current.innerHTML = "";
          window.google.accounts.id.renderButton(registerGoogleButtonRef.current, {
            type: "standard",
            theme: "outline",
            size: "large",
            text: "continue_with",
            shape: "rectangular",
            logo_alignment: "left",
            width: Math.min(Math.max(registerGoogleButtonRef.current.offsetWidth || 340, 240), 400),
          });

          hasRegisterRenderedRef.current = true;
          setGoogleReady(true);
        } catch (err) {
          console.warn("Failed to render Google button in Register:", err);
        }
      }
    };

    setupGoogle();
    const interval = setInterval(() => {
      if (hasRegisterRenderedRef.current) {
        clearInterval(interval);
        return;
      }
      if (window.google?.accounts?.id && isMounted) {
        setupGoogle();
        clearInterval(interval);
      }
    }, 200);
    const timeout = setTimeout(() => clearInterval(interval), 5000);

    return () => {
      isMounted = false;
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [googleClientId, method, googleStep, processGoogleToken]);



  // --------------------------------------------------------------------------
  // Option 1 Handlers: Email
  // --------------------------------------------------------------------------
  const handleSendEmailOtp = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await sendOtp(email, "registration");
      setEmailStep(2);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to send verification code."));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyEmailOtp = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await verifyOtp(email, otp, "registration");
      setVerificationToken(res.verification_token);
      setEmailStep(3);
    } catch (err) {
      setError(extractErrorMessage(err, "Invalid or expired verification code."));
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteEmailRegistration = async (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);
    try {
      const res = await registerEmail({
        verification_token: verificationToken,
        username,
        full_name: fullName,
        organization,
        requested_role: requestedRole,
        password,
        confirm_password: confirmPassword,
      });

      setSubmissionMessage(res.message);
      setIsSubmitted(true);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to complete registration."));
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // Option 2 Handlers: Google
  // --------------------------------------------------------------------------
  const handleGoogleSignInClick = () => {
    setError("");
    if (!googleClientId) {
      setError(
        "Google Sign-In is not configured. Please use Option 1 (Email Registration).",
      );
      return;
    }

    if (window.google?.accounts?.id) {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: (response) => {
          if (response?.credential) {
            processGoogleToken(response.credential);
          }
        },
      });
      window.google.accounts.id.prompt();
    } else {
      setError(
        "Google Identity Services could not be loaded. Please ensure accounts.google.com is accessible, or use Option 1 (Email Registration).",
      );
    }
  };

  const handleCompleteGoogleRegistration = async (e) => {
    e.preventDefault();
    setError("");

    if (googlePassword && googlePassword.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);
    try {
      const res = await registerGoogle({
        registration_token: googleRegToken,
        username: googleUsername,
        full_name: googleName,
        organization: googleOrg,
        requested_role: googleRole,
        password: googlePassword || undefined,
      });

      setSubmissionMessage(res.message);
      setIsSubmitted(true);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to complete Google registration."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#f7f8fa] px-4 py-8 text-[#102a43] sm:px-8 lg:px-12">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 flex items-center justify-between">
          <Link
            to="/login"
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft size={16} /> Back to Sign In
          </Link>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[#5a1725]">
            <ShieldCheck size={18} /> PharmaVerse AI Registration
          </div>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-7 shadow-lg sm:p-9">
          {isSubmitted ? (
            <div className="py-8 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                <Clock size={36} />
              </div>
              <h1 className="mt-5 text-2xl font-bold tracking-tight text-[#102a43]">
                Account Pending Approval
              </h1>
              <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-600">
                {submissionMessage ||
                  "Your registration has been submitted and is currently pending administrator approval. You will be able to sign in once an administrator approves your account."}
              </p>
              <div className="mt-8">
                <Link
                  to="/login"
                  className="inline-flex items-center justify-center rounded-lg bg-[#5a1725] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c]"
                >
                  Return to Sign In
                </Link>
              </div>
            </div>
          ) : (
            <div>
              <div className="mb-6 text-center">
                <h1 className="text-2xl font-bold tracking-tight text-[#102a43]">
                  Create your PharmaVerse Account
                </h1>
                <p className="mt-2 text-sm text-slate-600">
                  Select your preferred registration method below. All accounts require administrator approval.
                </p>
              </div>

              {/* Method Switcher Tabs */}
              <div className="mb-6 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => {
                    setMethod("email");
                    setError("");
                  }}
                  className={`rounded-lg py-2 text-xs font-bold uppercase tracking-wider transition ${
                    method === "email"
                      ? "bg-white text-[#5a1725] shadow-xs"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Option 1: Email Registration
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMethod("google");
                    setError("");
                  }}
                  className={`rounded-lg py-2 text-xs font-bold uppercase tracking-wider transition ${
                    method === "google"
                      ? "bg-white text-[#5a1725] shadow-xs"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Option 2: Continue with Google
                </button>
              </div>

              {error && (() => {
                const isInfo =
                  error.toLowerCase().includes("already exists using email and password") ||
                  error.toLowerCase().includes("please sign in using your email and password") ||
                  (error.toLowerCase().includes("already exists") && error.toLowerCase().includes("sign in"));
                if (isInfo) {
                  return (
                    <div className="mb-5 flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50/80 p-4 text-sm text-slate-700 shadow-xs">
                      <Info className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
                      <div className="flex-1 leading-relaxed">
                        <p className="font-semibold text-slate-900 mb-0.5">Account Notice</p>
                        <p>{error}</p>
                        <div className="mt-3">
                          <Link
                            to="/login"
                            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-700 shadow-xs"
                          >
                            Sign In to Your Account
                          </Link>
                        </div>
                      </div>
                    </div>
                  );
                }
                return (
                  <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                    {error}
                  </div>
                );
              })()}

              {/* OPTION 1: EMAIL REGISTRATION FLOW */}
              {method === "email" && (
                <div>
                  {emailStep === 1 && (
                    <form onSubmit={handleSendEmailOtp} className="space-y-4">
                      <div className="rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                        We require email ownership verification before account creation.
                        Enter your work email address to receive a secure 6-digit verification code.
                      </div>

                      <label className="block">
                        <span className="text-xs font-semibold text-slate-700">Work Email Address</span>
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="officer@pharmacy.com"
                          required
                          className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none transition focus:border-[#5a1725]"
                        />
                      </label>

                      <button
                        type="submit"
                        disabled={loading || !email}
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:opacity-60"
                      >
                        <Mail size={16} />
                        {loading ? "Sending Code..." : "Send Verification Code"}
                      </button>
                    </form>
                  )}

                  {emailStep === 2 && (
                    <form onSubmit={handleVerifyEmailOtp} className="space-y-4">
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>Code sent to <strong>{email}</strong></span>
                        <button
                          type="button"
                          onClick={() => setEmailStep(1)}
                          className="font-semibold text-[#5a1725] hover:underline"
                        >
                          Change
                        </button>
                      </div>

                      <label className="block">
                        <span className="text-xs font-semibold text-slate-700">Enter 6-Digit Code</span>
                        <input
                          type="text"
                          value={otp}
                          onChange={(e) => setOtp(e.target.value)}
                          placeholder="123456"
                          maxLength={10}
                          required
                          className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-center font-mono text-base tracking-widest text-[#102a43] outline-none transition focus:border-[#5a1725]"
                        />
                      </label>

                      <button
                        type="submit"
                        disabled={loading || !otp}
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:opacity-60"
                      >
                        <ShieldCheck size={16} />
                        {loading ? "Verifying..." : "Verify Code & Continue"}
                      </button>

                      <div className="text-center">
                        <button
                          type="button"
                          disabled={loading}
                          onClick={handleSendEmailOtp}
                          className="text-xs font-semibold text-slate-500 hover:text-slate-800"
                        >
                          Didn&apos;t receive code? Resend
                        </button>
                      </div>
                    </form>
                  )}

                  {emailStep === 3 && (
                    <form onSubmit={handleCompleteEmailRegistration} className="space-y-4">
                      <div className="rounded-lg bg-emerald-50 p-2.5 text-xs font-semibold text-emerald-800">
                        Verified email: {email}
                      </div>

                      <div className="grid gap-4 sm:grid-cols-2">
                        <label className="block">
                          <span className="text-xs font-semibold text-slate-700">Full Name</span>
                          <input
                            type="text"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            placeholder="Dr. Jane Smith"
                            required
                            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                          />
                        </label>
                        <label className="block">
                          <span className="text-xs font-semibold text-slate-700">Username</span>
                          <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="janesmith"
                            required
                            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                          />
                        </label>
                      </div>

                      <div className="grid gap-4 sm:grid-cols-2">
                        <label className="block">
                          <span className="text-xs font-semibold text-slate-700">Organization</span>
                          <input
                            type="text"
                            value={organization}
                            onChange={(e) => setOrganization(e.target.value)}
                            placeholder="Apex Healthcare Labs"
                            required
                            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                          />
                        </label>
                        <label className="block">
                          <span className="text-xs font-semibold text-slate-700">Requested Supply Chain Role</span>
                          <select
                            value={requestedRole}
                            onChange={(e) => setRequestedRole(e.target.value)}
                            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                          >
                            {ALLOWED_ROLES.map((r) => (
                              <option key={r.value} value={r.value}>
                                {r.label}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>

                      <div className="grid gap-4 sm:grid-cols-2">
                        <label className="block">
                          <span className="text-xs font-semibold text-slate-700">Password</span>
                          <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Min. 8 characters"
                            required
                            minLength={8}
                            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                          />
                        </label>
                        <label className="block">
                          <span className="text-xs font-semibold text-slate-700">Confirm Password</span>
                          <input
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="Repeat password"
                            required
                            minLength={8}
                            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                          />
                        </label>
                      </div>

                      <button
                        type="submit"
                        disabled={loading || !username || !password || !confirmPassword}
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:opacity-60"
                      >
                        <UserCheck size={16} />
                        {loading ? "Submitting Registration..." : "Complete Registration for Approval"}
                      </button>
                    </form>
                  )}
                </div>
              )}

              {/* OPTION 2: GOOGLE SIGN-IN FLOW */}
              {method === "google" && (
                <div>
                  {googleStep === 1 ? (
                    <div className="space-y-4 py-4 text-center">
                      <p className="text-sm text-slate-600">
                        Sign in with your verified Google account to authenticate.
                        Once authenticated, you will specify your organization details and requested role.
                      </p>

                      <div className="flex w-full flex-col items-center justify-center">
                        <div
                          ref={registerGoogleButtonRef}
                          className={`flex min-h-[44px] w-full items-center justify-center ${!googleReady ? "hidden" : ""}`}
                        />
                        {!googleReady && (
                          <button
                            type="button"
                            onClick={handleGoogleSignInClick}
                            disabled={loading}
                            className="mx-auto flex w-full max-w-sm items-center justify-center gap-3 rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 disabled:opacity-60"
                          >
                            <GoogleIcon />
                            {loading ? "Verifying Google Identity..." : "Continue with Google"}
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <form onSubmit={handleCompleteGoogleRegistration} className="space-y-4">
                      <div className="flex items-center justify-between rounded-lg bg-emerald-50 p-3 text-xs text-emerald-800">
                        <div>
                          <strong>Verified Google Identity:</strong> {googleName} ({googleEmail})
                        </div>
                        <button
                          type="button"
                          onClick={() => setGoogleStep(1)}
                          className="text-xs font-semibold text-emerald-900 underline"
                        >
                          Change
                        </button>
                      </div>

                      <div className="grid gap-4 sm:grid-cols-2">
                        <label className="block">
                          <span className="text-xs font-semibold text-slate-700">Username</span>
                          <input
                            type="text"
                            value={googleUsername}
                            onChange={(e) => setGoogleUsername(e.target.value)}
                            required
                            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                          />
                        </label>
                        <label className="block">
                          <span className="text-xs font-semibold text-slate-700">Organization</span>
                          <input
                            type="text"
                            value={googleOrg}
                            onChange={(e) => setGoogleOrg(e.target.value)}
                            placeholder="Healthcare Organization"
                            required
                            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                          />
                        </label>
                      </div>

                      <label className="block">
                        <span className="text-xs font-semibold text-slate-700">Requested Supply Chain Role</span>
                        <select
                          value={googleRole}
                          onChange={(e) => setGoogleRole(e.target.value)}
                          className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                        >
                          {ALLOWED_ROLES.map((r) => (
                            <option key={r.value} value={r.value}>
                              {r.label}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="block">
                        <span className="text-xs font-semibold text-slate-700">Sign-in Password (Optional)</span>
                        <input
                          type="password"
                          value={googlePassword}
                          onChange={(e) => setGooglePassword(e.target.value)}
                          placeholder="Optional password for email sign-in once approved (min 8 chars)"
                          minLength={8}
                          className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                        />
                      </label>

                      <button
                        type="submit"
                        disabled={loading || !googleUsername || !googleOrg}
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:opacity-60"
                      >
                        <UserCheck size={16} />
                        {loading ? "Submitting Registration..." : "Submit Registration for Approval"}
                      </button>
                    </form>
                  )}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
