import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Boxes,
  ClipboardList,
  LayoutDashboard,
  PackageSearch,
  QrCode,
  ShieldCheck,
  Truck,
  UserRound,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { getStoredUser } from "../../services/authService";
import { ROLE_ACCESS } from "../../utils/roles";
import { useAuth } from "../../context/AuthContext";

const sections = [
  {
    title: "Overview",
    items: [
      {
        label: "Dashboard",
        path: "/dashboard",
        icon: LayoutDashboard,
        roles: ROLE_ACCESS.all,
      },
    ],
  },
  {
    title: "Supply Chain",
    items: [
      {
        label: "Drugs",
        path: "/drugs",
        icon: PackageSearch,
        roles: ROLE_ACCESS.drugs,
      },
      {
        label: "Batches",
        path: "/batches",
        icon: Boxes,
        roles: ROLE_ACCESS.batches,
      },
      {
        label: "Shipments",
        path: "/shipments",
        icon: Truck,
        roles: ROLE_ACCESS.shipments,
      },
      {
        label: "QR & RFID",
        path: "/identities",
        icon: QrCode,
        roles: ROLE_ACCESS.identity,
      },
    ],
  },
  {
    title: "Monitoring",
    items: [
      {
        label: "Simulation",
        path: "/simulation",
        icon: Activity,
        roles: ROLE_ACCESS.simulation,
      },
      {
        label: "AI Alerts",
        path: "/alerts",
        icon: AlertTriangle,
        roles: ROLE_ACCESS.ai,
      },
      {
        label: "AI Research",
        path: "/ai-research",
        icon: BrainCircuit,
        roles: ROLE_ACCESS.oversight,
      },
    ],
  },
  {
    title: "Verification",
    items: [
      {
        label: "Medicine Verification",
        path: "/verification",
        icon: QrCode,
        roles: ROLE_ACCESS.verification,
      },
      {
        label: "Blockchain",
        path: "/blockchain",
        icon: ShieldCheck,
        roles: ROLE_ACCESS.oversight,
      },
      {
        label: "Audit Trail",
        path: "/audit",
        icon: ClipboardList,
        roles: ROLE_ACCESS.oversight,
      },
    ],
  },
];

export default function Sidebar({ isOpen = false, onNavigate }) {
  const authUser = useAuth();
  const role = authUser?.role || getStoredUser()?.role;

  return (
    <aside
      className={[
        "fixed inset-y-0 left-0 z-40 w-64 shrink-0 border-r border-slate-200 bg-white shadow-xl transition-transform duration-200 lg:sticky lg:top-0 lg:block lg:translate-x-0 lg:shadow-none",
        isOpen ? "translate-x-0" : "-translate-x-full",
      ].join(" ")}
    >
      <div className="sticky top-0 flex h-screen flex-col">
        {/* Brand */}
        <div className="border-b border-slate-200 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#5a1725] text-white shadow-sm">
              <ShieldCheck size={22} strokeWidth={2} />
            </div>

            <div>
              <div className="text-base font-bold tracking-tight text-[#102a43]">
                PharmaVerse
              </div>

              <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#5a1725]">
                AI Platform
              </div>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-5">
          <div className="space-y-6">
            {sections.map((section) => (
              <div key={section.title}>
                <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                  {section.title}
                </p>

                <div className="space-y-1">
                  {section.items.filter((item) => item.roles.includes(role)).map((item) => {
                    const Icon = item.icon;

                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        onClick={onNavigate}
                        className={({ isActive }) =>
                          [
                            "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                            isActive
                              ? "bg-[#5a1725] text-white shadow-sm"
                              : "text-slate-600 hover:bg-[#f7f8fa] hover:text-[#102a43]",
                          ].join(" ")
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <Icon
                              size={18}
                              strokeWidth={isActive ? 2.3 : 2}
                            />

                            <span>{item.label}</span>
                          </>
                        )}
                      </NavLink>
                    );
                  })}
                </div>
              </div>
            ))}
            {role === "ADMIN" && (
              <div>
                <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Administration</p>
                <NavLink
                  to="/admin/dashboard"
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    [
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                      isActive ? "bg-[#5a1725] text-white shadow-sm" : "text-slate-600 hover:bg-[#f7f8fa] hover:text-[#102a43]",
                    ].join(" ")
                  }
                >
                  <ShieldCheck size={18} />
                  <span>Admin Dashboard</span>
                </NavLink>
              </div>
            )}
          </div>
        </nav>

        {/* Account */}
        <div className="border-t border-slate-200 p-3">
          <NavLink
            to="/profile"
            onClick={onNavigate}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                isActive
                  ? "bg-[#102a43] text-white"
                  : "text-slate-600 hover:bg-slate-50 hover:text-[#102a43]",
              ].join(" ")
            }
          >
            <UserRound size={18} />
            <span>Profile</span>
          </NavLink>
          <NavLink
            to="/settings"
            onClick={onNavigate}
            className={({ isActive }) =>
              [
                "mt-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                isActive
                  ? "bg-[#102a43] text-white"
                  : "text-slate-600 hover:bg-slate-50 hover:text-[#102a43]",
              ].join(" ")
            }
          >
            <ShieldCheck size={18} />
            <span>Settings</span>
          </NavLink>
        </div>
      </div>
    </aside>
  );
}
