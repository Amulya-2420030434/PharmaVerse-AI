import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { getCurrentUser, linkGoogleAccount, setTwoFactorEnabled } from "../services/authService";
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

export default function Settings() {
  const [user, setUser] = useState(null);
  const [enabled, setEnabled] = useState(false);
  const [hasGoogleLinked, setHasGoogleLinked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const googleLinkButtonRef = useRef(null);
  const [googleReady, setGoogleReady] = useState(false);

  const handleLinkGoogle = useCallback(async (idToken) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const res = await linkGoogleAccount(idToken);
      setHasGoogleLinked(true);
      setNotice(res.message || "Google account successfully linked to your PharmaVerse account.");
      const updatedUser = await getCurrentUser();
      setUser(updatedUser);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to link Google account."));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((userData) => {
        if (active) {
          setUser(userData);
          setEnabled(Boolean(userData.two_factor_enabled));
          setHasGoogleLinked(Boolean(userData.has_google_linked || userData.auth_provider === "google"));
        }
      })
      .catch((requestError) => {
        if (active) setError(extractErrorMessage(requestError, "Unable to load account settings."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!googleClientId || hasGoogleLinked) return;

    let isMounted = true;
    const setupGoogle = () => {
      if (window.google?.accounts?.id && googleLinkButtonRef.current && isMounted) {
        setGoogleReady(true);
        try {
          window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: (response) => {
              if (response?.credential) {
                handleLinkGoogle(response.credential);
              }
            },
            auto_select: false,
            cancel_on_tap_outside: true,
          });

          googleLinkButtonRef.current.innerHTML = "";
          window.google.accounts.id.renderButton(googleLinkButtonRef.current, {
            type: "standard",
            theme: "outline",
            size: "medium",
            text: "continue_with",
            shape: "rectangular",
            logo_alignment: "left",
          });
        } catch (err) {
          console.warn("Failed to render Google link button:", err);
        }
      }
    };

    setupGoogle();
    const interval = setInterval(() => {
      if (window.google?.accounts?.id && isMounted) {
        setupGoogle();
        clearInterval(interval);
      }
    }, 250);
    const timeout = setTimeout(() => clearInterval(interval), 4000);

    return () => {
      isMounted = false;
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [googleClientId, hasGoogleLinked, handleLinkGoogle]);

  const updateSetting = async (event) => {
    const nextEnabled = event.target.checked;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await setTwoFactorEnabled(nextEnabled);
      setEnabled(result.two_factor_enabled);
      setNotice(nextEnabled ? "Email two-factor authentication is enabled." : "Email two-factor authentication is disabled.");
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to update two-factor settings."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="max-w-3xl space-y-6">
      <h1 className="text-3xl font-bold text-[#102a43]">Settings</h1>

      {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">{error}</p>}
      {notice && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3.5 text-sm text-emerald-900">{notice}</p>}

      {/* Account Security (2FA) */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <h2 className="text-lg font-semibold text-[#102a43]">Account security</h2>
        <p className="mt-2 text-sm text-slate-600">Require a one-time code sent to your email after password or Google sign-in.</p>
        <label className="mt-5 flex items-center gap-3 text-sm font-medium text-slate-800">
          <input type="checkbox" checked={enabled} disabled={loading || busy} onChange={updateSetting} className="h-4 w-4 accent-[#5a1725]" />
          Enable email two-factor authentication
        </label>
        {!loading && <p className="mt-3 text-xs text-slate-500">A valid SMTP configuration is required for sign-in codes.</p>}
      </div>

      {/* Linked Identities (Google) */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <h2 className="text-lg font-semibold text-[#102a43]">Connected authentication methods</h2>
        <p className="mt-2 text-sm text-slate-600">
          Link your Google account to enable seamless Sign in with Google alongside your email and password.
        </p>

        <div className="mt-5 flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white shadow-xs border border-slate-200">
              <GoogleIcon />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-800">Google Account</p>
              <p className="text-xs text-slate-500">
                {hasGoogleLinked
                  ? "Your Google account is securely linked."
                  : user?.email
                  ? `Must match your registered email (${user.email})`
                  : "Requires matching verified email."}
              </p>
            </div>
          </div>

          <div>
            {hasGoogleLinked ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
                <CheckCircle2 size={14} />
                Linked
              </span>
            ) : (
              <div className="flex items-center gap-2">
                <div ref={googleLinkButtonRef} className={!googleReady ? "hidden" : ""} />
                {!googleReady && (
                  <span className="text-xs text-slate-400">Loading Google...</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
