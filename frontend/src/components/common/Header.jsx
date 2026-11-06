import { LogOut, Menu, UserRound } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { logout } from "../../services/authService";
import NotificationBell from "./NotificationBell";

export default function Header({ onMenuClick }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-[#5a1725] focus:outline-none focus:ring-2 focus:ring-[#5a1725]/20 lg:hidden"
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5a1725]">
              Pharmaceutical Supply Chain
            </p>
            <h1 className="text-sm font-semibold text-[#102a43] sm:text-base">
              PharmaVerse AI
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <NotificationBell />

          <button
            type="button"
            onClick={() => navigate("/profile")}
            className="hidden items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 sm:flex"
          >
            <UserRound size={18} />
            <span>Profile</span>
          </button>

          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-[#5a1725] transition hover:border-[#5a1725] hover:bg-[#5a1725] hover:text-white"
            title="Logout"
            aria-label="Logout"
          >
            <LogOut size={17} />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
