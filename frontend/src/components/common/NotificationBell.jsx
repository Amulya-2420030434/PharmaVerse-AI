import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, Check, Clock, ExternalLink, UserCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../../services/api";
import { getStoredUser } from "../../services/authService";

export default function NotificationBell() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [counts, setCounts] = useState({ pending: 0, unread: 0, total: 0 });
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  const user = getStoredUser();
  const isAdmin = user?.role === "ADMIN";

  const fetchCounts = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const response = await api.get("/notifications/count");
      setCounts(response.data || { pending: 0, unread: 0, total: 0 });
    } catch {
      // Non-blocking for header
    }
  }, [isAdmin]);

  const fetchNotifications = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const response = await api.get("/notifications?limit=20");
      setNotifications(response.data || []);
    } catch {
      // Non-blocking
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;
    let isMounted = true;

    const loadInitialCounts = async () => {
      try {
        const response = await api.get("/notifications/count");
        if (isMounted) {
          setCounts(response.data || { pending: 0, unread: 0, total: 0 });
        }
      } catch {
        // Non-blocking for header
      }
    };
    loadInitialCounts();

    const handleUpdate = () => {
      fetchCounts();
      if (isOpen) fetchNotifications();
    };

    window.addEventListener("notifications-updated", handleUpdate);
    // Periodic refresh every 30 seconds
    const interval = setInterval(fetchCounts, 30000);

    return () => {
      isMounted = false;
      window.removeEventListener("notifications-updated", handleUpdate);
      clearInterval(interval);
    };
  }, [isAdmin, fetchCounts, fetchNotifications, isOpen]);

  // Handle outside click to close dropdown
  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleOutsideClick);
    }
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [isOpen]);

  const handleToggle = () => {
    const nextOpen = !isOpen;
    setIsOpen(nextOpen);
    if (nextOpen) {
      fetchNotifications();
    }
  };

  const handleNotificationClick = async (notif) => {
    try {
      if (!notif.is_read) {
        await api.post(`/notifications/${notif.id}/read`);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n)),
        );
        fetchCounts();
      }
    } catch {
      // Continue navigation even if read receipt fails
    }
    setIsOpen(false);
    navigate("/admin/dashboard");
  };

  const handleMarkAllRead = async (event) => {
    event.stopPropagation();
    try {
      await api.post("/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      fetchCounts();
    } catch {
      // Non-blocking
    }
  };

  if (!isAdmin) {
    return null;
  }

  const pendingCount = counts.pending || 0;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={handleToggle}
        className="relative rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-[#102a43] focus:outline-none focus:ring-2 focus:ring-[#5a1725]/20"
        aria-label="Admin Notifications"
        title={pendingCount > 0 ? `${pendingCount} pending registration approvals` : "Notifications"}
      >
        <Bell size={19} />
        {pendingCount > 0 ? (
          <span
            data-testid="notification-badge"
            className="absolute -top-1 -right-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-[#5a1725] px-1 text-[11px] font-bold text-white shadow-sm ring-2 ring-white"
          >
            {pendingCount > 99 ? "99+" : pendingCount}
          </span>
        ) : null}
      </button>

      {isOpen && (
        <div
          data-testid="notification-dropdown"
          className="absolute right-0 top-full mt-2 w-80 sm:w-96 rounded-xl border border-slate-200 bg-white p-0 shadow-xl z-50 overflow-hidden"
        >
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/80 px-4 py-3">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-sm text-[#102a43]">Notifications</h3>
              {pendingCount > 0 && (
                <span className="rounded-full bg-[#5a1725]/10 px-2 py-0.5 text-xs font-semibold text-[#5a1725]">
                  {pendingCount} pending
                </span>
              )}
            </div>
            {notifications.some((n) => !n.is_read) && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-[#5a1725] transition"
              >
                <Check size={14} />
                <span>Mark read</span>
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
            {loading ? (
              <div className="p-6 text-center text-sm text-slate-400">Loading notifications…</div>
            ) : notifications.length === 0 ? (
              <div className="p-6 text-center text-sm text-slate-500">
                <UserCheck size={28} className="mx-auto mb-2 text-slate-300" />
                No pending approval requests.
              </div>
            ) : (
              notifications.map((notif) => {
                const isPending = notif.status === "PENDING";
                const isApproved = notif.status === "APPROVED";
                const isRejected = notif.status === "REJECTED";

                return (
                  <div
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    className={`cursor-pointer p-3.5 transition hover:bg-slate-50 flex items-start gap-3 ${
                      !notif.is_read ? "bg-amber-50/40" : ""
                    }`}
                  >
                    <div
                      className={`mt-0.5 rounded-full p-1.5 flex-shrink-0 ${
                        isPending
                          ? "bg-amber-100 text-amber-700"
                          : isApproved
                          ? "bg-emerald-100 text-emerald-700"
                          : isRejected
                          ? "bg-rose-100 text-rose-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      <Clock size={15} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-semibold text-[#102a43] truncate">
                          {notif.applicant_name || notif.title}
                        </p>
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                            isPending
                              ? "bg-amber-100 text-amber-800"
                              : isApproved
                              ? "bg-emerald-100 text-emerald-800"
                              : isRejected
                              ? "bg-rose-100 text-rose-800"
                              : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {notif.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 truncate mt-0.5">
                        {notif.applicant_email}
                      </p>
                      <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-slate-400">
                        <span>Role: <strong className="text-slate-600">{notif.applicant_role || "—"}</strong></span>
                        <span>{new Date(notif.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="border-t border-slate-100 bg-slate-50/50 p-2 text-center">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                navigate("/admin/dashboard");
              }}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#5a1725] hover:underline"
            >
              <span>Manage all approvals in Admin Dashboard</span>
              <ExternalLink size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

