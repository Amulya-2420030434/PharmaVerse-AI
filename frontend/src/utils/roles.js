export const ROLE_ACCESS = {
  all: ["ADMIN", "REGULATOR", "MANUFACTURER", "DISTRIBUTOR", "TRANSPORTER", "PHARMACY"],
  drugs: ["ADMIN", "REGULATOR", "MANUFACTURER", "DISTRIBUTOR", "PHARMACY"],
  batches: ["ADMIN", "REGULATOR", "MANUFACTURER"],
  shipments: ["ADMIN", "REGULATOR", "MANUFACTURER", "DISTRIBUTOR", "TRANSPORTER"],
  ai: ["ADMIN", "REGULATOR", "DISTRIBUTOR", "TRANSPORTER", "PHARMACY"],
  verification: ["ADMIN", "REGULATOR", "PHARMACY"],
  oversight: ["ADMIN", "REGULATOR"],
  simulation: ["ADMIN", "REGULATOR"],
  identity: ["ADMIN", "REGULATOR", "MANUFACTURER", "DISTRIBUTOR", "TRANSPORTER", "PHARMACY"],
  notifications: ["ADMIN"],
};

export const canViewNotifications = (role) => role === "ADMIN";
