import { useCallback, useEffect, useRef, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Info,
  KeyRound,
  LockKeyhole,
  Mail,
  ShieldCheck,
  X,
} from "lucide-react";

import {
  getStoredUser,
  login,
  loginWithGoogle,
  resetPassword,
  sendOtp,
} from "../services/authService";
import { getAuthDestination } from "../utils/authNavigation";
import { extractErrorMessage } from "../utils/error";

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

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Forgot password modal state
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [resetStep, setResetStep] = useState(1); // 1: request OTP, 2: verify & change password
  const [resetEmail, setResetEmail] = useState("");
  const [resetOtp, setResetOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState("");
  const [resetSuccess, setResetSuccess] = useState("");

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const notice = location.state?.notice || "";
  const googleButtonRef = useRef(null);
  const hasRenderedRef = useRef(false);
  const [googleReady, setGoogleReady] = useState(false);

  const isAuthenticated = Boolean(
    localStorage.getItem("access_token") && getStoredUser(),
  );

  const handleProcessGoogleToken = useCallback(
    async (credential) => {
      setIsSubmitting(true);
      setError("");
      let credentialEmail = "";
      try {
        if (typeof credential === "string" && credential.includes(".")) {
          const base64Url = credential.split(".")[1];
          const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
          const jsonPayload = decodeURIComponent(
            atob(base64)
              .split("")
              .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
              .join(""),
          );
          const parsed = JSON.parse(jsonPayload);
          if (parsed?.email) {
            credentialEmail = parsed.email;
          }
        }
      } catch {
        // Fallback silently if credential payload decode fails
      }

      try {
        const result = await loginWithGoogle(credential);
        if (result?.existing_user === false) {
          setError(
            result?.message ||
              "No PharmaVerse account found for this Google identity. Please register an account first.",
          );
          return;
        }
        const destination = getAuthDestination(result);
        if (!destination) {
          throw new Error("Google sign-in returned an incomplete response.");
        }
        navigate(destination.path, {
          state: destination.state,
          replace: true,
        });
      } catch (err) {
        if (credentialEmail) {
          setEmail(credentialEmail);
        }
        setError(extractErrorMessage(err, "Google sign-in failed."));
      } finally {
        setIsSubmitting(false);
      }
    },
    [navigate],
  );

  useEffect(() => {
    if (!googleClientId) return;

    let isMounted = true;

    const setupGoogle = () => {
      if (
        !hasRenderedRef.current &&
        window.google?.accounts?.id &&
        googleButtonRef.current &&
        isMounted
      ) {
        try {
          window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: (response) => {
              if (response?.credential) {
                handleProcessGoogleToken(response.credential);
              }
            },
            auto_select: false,
            cancel_on_tap_outside: true,
          });

          googleButtonRef.current.innerHTML = "";
          window.google.accounts.id.renderButton(googleButtonRef.current, {
            type: "standard",
            theme: "outline",
            size: "large",
            text: "continue_with",
            shape: "rectangular",
            logo_alignment: "left",
            width: Math.min(Math.max(googleButtonRef.current.offsetWidth || 340, 240), 400),
          });

          hasRenderedRef.current = true;
          setGoogleReady(true);
        } catch (err) {
          console.warn("Failed to render Google Sign-In button:", err);
        }
      }
    };

    setupGoogle();
    const interval = setInterval(() => {
      if (hasRenderedRef.current) {
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
  }, [googleClientId, handleProcessGoogleToken]);

  const handleGoogleClick = () => {
    setError("");
    if (!googleClientId) {
      setError(
        "Google Sign-In is not configured. Please use your email and password to sign in.",
      );
      return;
    }

    if (window.google?.accounts?.id) {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: (response) => {
          if (response?.credential) {
            handleProcessGoogleToken(response.credential);
          }
        },
      });
      window.google.accounts.id.prompt();
    } else {
      setError(
        "Google Identity Services could not be loaded. Please ensure accounts.google.com is accessible, or use your email and password to sign in.",
      );
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const result = await login(email, password);
      const destination = getAuthDestination(result);
      if (!destination) {
        throw new Error("Sign-in returned an unexpected response.");
      }
      navigate(destination.path, { state: destination.state, replace: true });
    } catch (err) {
      setError(
        extractErrorMessage(
          err,
          "Unable to sign in. Please verify your email and password.",
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendResetOtp = async (e) => {
    e.preventDefault();
    setResetError("");
    setResetLoading(true);

    try {
      await sendOtp(resetEmail, "password_reset");
      setResetStep(2);
    } catch (err) {
      setResetError(extractErrorMessage(err, "Failed to send reset code."));
    } finally {
      setResetLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setResetError("");

    if (newPassword !== confirmPassword) {
      setResetError("New passwords do not match.");
      return;
    }

    if (newPassword.length < 8) {
      setResetError("Password must be at least 8 characters long.");
      return;
    }

    setResetLoading(true);
    try {
      const res = await resetPassword({
        email: resetEmail,
        otp: resetOtp,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setResetSuccess(
        res.message || "Password reset successfully. You can now sign in.",
      );
      setTimeout(() => {
        setShowForgotModal(false);
        setResetStep(1);
        setResetSuccess("");
        setEmail(resetEmail);
      }, 2000);
    } catch (err) {
      setResetError(
        extractErrorMessage(err, "Failed to reset password. Please check the code."),
      );
    } finally {
      setResetLoading(false);
    }
  };

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="min-h-screen bg-[#f7f8fa] px-4 py-8 text-[#102a43] sm:px-8 lg:px-12">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-10 lg:grid-cols-[1fr_420px]">
        {/* Brand Showcase Section */}
        <section className="hidden rounded-2xl bg-[#102a43] p-10 text-white shadow-lg lg:block">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#5a1725]">
            <ShieldCheck size={24} />
          </div>

          <p className="mt-8 text-xs font-bold uppercase tracking-[0.18em] text-rose-200">
            Intelligent pharmaceutical supply chain
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-tight">
            Trusted traceability for modern medicine.
          </h1>

          <p className="mt-5 max-w-lg text-sm leading-7 text-slate-300">
            PharmaVerse AI brings pharmaceutical identity, supply-chain
            monitoring, and verification workflows into one focused platform.
          </p>
        </section>

        {/* Sign In Form Section */}
        <section className="w-full rounded-2xl border border-slate-200 bg-white p-7 shadow-lg sm:p-8">
          <div className="mb-8">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#5a1725] text-white lg:hidden">
              <ShieldCheck size={23} />
            </div>

            <p className="mt-6 text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">
              PharmaVerse AI
            </p>

            <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#102a43]">
              Sign in to the platform
            </h1>

            <p className="mt-3 text-sm leading-6 text-slate-600">
              Enter your registered email address or username and password to access the system.
            </p>
          </div>

          {notice && (
            <div className="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              {notice}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">
                Email Address or Username
              </span>
              <input
                type="text"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                placeholder="name@organization.com"
                className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-[#102a43] outline-none transition placeholder:text-slate-400 focus:border-[#5a1725] focus:ring-2 focus:ring-[#5a1725]/10"
                required
              />
            </label>

            <label className="block">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Password</span>
                <button
                  type="button"
                  onClick={() => {
                    setResetEmail(email);
                    setResetStep(1);
                    setResetError("");
                    setResetSuccess("");
                    setShowForgotModal(true);
                  }}
                  className="text-xs font-semibold text-[#5a1725] hover:underline"
                >
                  Forgot password?
                </button>
              </div>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                placeholder="Enter your password"
                className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-[#102a43] outline-none transition placeholder:text-slate-400 focus:border-[#5a1725] focus:ring-2 focus:ring-[#5a1725]/10"
                required
              />
            </label>

            {error && (() => {
              const isInfo =
                error.toLowerCase().includes("already exists using email and password") ||
                error.toLowerCase().includes("please sign in using your email and password") ||
                error.toLowerCase().includes("register an account first") ||
                (error.toLowerCase().includes("already exists") && error.toLowerCase().includes("sign in"));
              if (isInfo) {
                return (
                  <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50/80 p-3.5 text-sm text-slate-700">
                    <Info className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
                    <div className="flex-1 leading-relaxed">
                      <p className="font-semibold text-slate-900 mb-0.5">Account Notice</p>
                      <p>{error}</p>
                      {error.toLowerCase().includes("register") && (
                        <div className="mt-2.5">
                          <Link
                            to="/register"
                            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-700"
                          >
                            Register with Google
                          </Link>
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
              return (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </div>
              );
            })()}

            <button
              type="submit"
              disabled={isSubmitting}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#43111c] disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-[#5a1725]/30 focus:ring-offset-2"
            >
              <LockKeyhole size={17} />
              {isSubmitting ? "Signing in..." : "Continue to dashboard"}
            </button>
          </form>

          {/* Optional Google Sign-In divider & button */}
          {googleClientId && (
            <>
              <div className="my-5 flex items-center gap-3 text-xs text-slate-400">
                <span className="h-px flex-1 bg-slate-200" />
                OR
                <span className="h-px flex-1 bg-slate-200" />
              </div>

              <div className="flex w-full flex-col items-center justify-center">
                <div
                  ref={googleButtonRef}
                  className={`flex min-h-[44px] w-full items-center justify-center ${!googleReady ? "hidden" : ""}`}
                />
                {!googleReady && (
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={handleGoogleClick}
                    className="flex w-full items-center justify-center gap-2.5 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 disabled:opacity-60"
                  >
                    <GoogleIcon />
                    Continue with Google
                  </button>
                )}
              </div>
            </>
          )}

          <div className="mt-6 border-t border-slate-100 pt-5 text-center text-sm text-slate-600">
            Don&apos;t have an account?{" "}
            <Link
              to="/register"
              className="font-semibold text-[#5a1725] transition hover:underline"
            >
              Register here
            </Link>
          </div>
        </section>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl sm:p-7">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-[#102a43]">Reset Password</h3>
              <button
                type="button"
                onClick={() => setShowForgotModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X size={18} />
              </button>
            </div>

            {resetSuccess ? (
              <div className="py-6 text-center">
                <CheckCircle2 className="mx-auto text-emerald-600" size={42} />
                <p className="mt-3 text-sm font-semibold text-slate-800">{resetSuccess}</p>
              </div>
            ) : resetStep === 1 ? (
              <form onSubmit={handleSendResetOtp} className="mt-4 space-y-4">
                <p className="text-sm text-slate-600">
                  Enter your account email. We will send you a 6-digit verification code.
                </p>
                <label className="block">
                  <span className="text-xs font-semibold text-slate-700">Account Email</span>
                  <input
                    type="email"
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                    placeholder="name@organization.com"
                    required
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                  />
                </label>

                {resetError && (
                  <div className="rounded-lg bg-red-50 p-2.5 text-xs text-red-700">
                    {resetError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={resetLoading || !resetEmail}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2 text-sm font-semibold text-white hover:bg-[#43111c] disabled:opacity-60"
                >
                  <Mail size={16} />
                  {resetLoading ? "Sending code..." : "Send Reset Code"}
                </button>
              </form>
            ) : (
              <form onSubmit={handleResetPassword} className="mt-4 space-y-4">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setResetStep(1)}
                    className="flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-700"
                  >
                    <ArrowLeft size={14} /> Change email ({resetEmail})
                  </button>
                </div>

                <label className="block">
                  <span className="text-xs font-semibold text-slate-700">6-Digit Code</span>
                  <input
                    type="text"
                    value={resetOtp}
                    onChange={(e) => setResetOtp(e.target.value)}
                    placeholder="123456"
                    maxLength={10}
                    required
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-center font-mono text-base tracking-widest text-[#102a43] outline-none focus:border-[#5a1725]"
                  />
                </label>

                <label className="block">
                  <span className="text-xs font-semibold text-slate-700">New Password</span>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    required
                    minLength={8}
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-[#102a43] outline-none focus:border-[#5a1725]"
                  />
                </label>

                <label className="block">
                  <span className="text-xs font-semibold text-slate-700">Confirm New Password</span>
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

                {resetError && (
                  <div className="rounded-lg bg-red-50 p-2.5 text-xs text-red-700">
                    {resetError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={resetLoading || !resetOtp || !newPassword}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2 text-sm font-semibold text-white hover:bg-[#43111c] disabled:opacity-60"
                >
                  <KeyRound size={16} />
                  {resetLoading ? "Resetting..." : "Save New Password"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </main>
  );
}