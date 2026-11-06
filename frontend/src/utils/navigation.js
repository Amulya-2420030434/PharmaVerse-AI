import {
  LayoutDashboard,
  Pill,
  Package,
  Truck,
  ShieldAlert,
  ScanLine,
  Blocks,
  ClipboardList
} from "lucide-react";

export const navigationItems = [
  {
    label: "Dashboard",
    path: "/dashboard",
    icon: LayoutDashboard,
    roles: [
      "ADMIN",
      "REGULATOR",
      "MANUFACTURER",
      "DISTRIBUTOR",
      "TRANSPORTER",
      "PHARMACY"
    ]
  },
  {
    label: "Drugs",
    path: "/drugs",
    icon: Pill,
    roles: [
      "ADMIN",
      "REGULATOR",
      "MANUFACTURER",
      "DISTRIBUTOR",
      "PHARMACY"
    ]
  },
  {
    label: "Batches",
    path: "/batches",
    icon: Package,
    roles: [
      "ADMIN",
      "REGULATOR",
      "MANUFACTURER"
    ]
  },
  {
    label: "Shipments",
    path: "/shipments",
    icon: Truck,
    roles: [
      "ADMIN",
      "REGULATOR",
      "MANUFACTURER",
      "DISTRIBUTOR",
      "TRANSPORTER"
    ]
  },
  {
    label: "AI Alerts",
    path: "/alerts",
    icon: ShieldAlert,
    roles: [
      "ADMIN",
      "REGULATOR",
      "DISTRIBUTOR",
      "TRANSPORTER",
      "PHARMACY"
    ]
  },
  {
    label: "Verification",
    path: "/verification",
    icon: ScanLine,
    roles: [
      "ADMIN",
      "REGULATOR",
      "PHARMACY"
    ]
  },
  {
    label: "Blockchain",
    path: "/blockchain",
    icon: Blocks,
    roles: [
      "ADMIN",
      "REGULATOR"
    ]
  },
  {
    label: "Audit Trail",
    path: "/audit",
    icon: ClipboardList,
    roles: [
      "ADMIN",
      "REGULATOR"
    ]
  }
];
