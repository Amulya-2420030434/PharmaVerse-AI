import assert from "node:assert/strict";
import test from "node:test";

import { ROLE_ACCESS, canViewNotifications } from "./roles.js";

test("only ADMIN role can view and access notifications", () => {
  assert.equal(canViewNotifications("ADMIN"), true);
  assert.equal(canViewNotifications("MANUFACTURER"), false);
  assert.equal(canViewNotifications("DISTRIBUTOR"), false);
  assert.equal(canViewNotifications("PHARMACY"), false);
  assert.equal(canViewNotifications("TRANSPORTER"), false);
  assert.equal(canViewNotifications("REGULATOR"), false);
  assert.equal(canViewNotifications("VIEWER"), false);
  assert.equal(canViewNotifications(null), false);
  assert.equal(canViewNotifications(undefined), false);
});

test("ROLE_ACCESS.notifications is strictly restricted to ADMIN", () => {
  assert.deepEqual(ROLE_ACCESS.notifications, ["ADMIN"]);
  assert.equal(ROLE_ACCESS.notifications.includes("MANUFACTURER"), false);
  assert.equal(ROLE_ACCESS.notifications.includes("DISTRIBUTOR"), false);
  assert.equal(ROLE_ACCESS.notifications.includes("PHARMACY"), false);
  assert.equal(ROLE_ACCESS.notifications.includes("TRANSPORTER"), false);
  assert.equal(ROLE_ACCESS.notifications.includes("REGULATOR"), false);
});

