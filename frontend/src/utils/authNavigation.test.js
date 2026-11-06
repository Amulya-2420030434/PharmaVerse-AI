import assert from "node:assert/strict";
import test from "node:test";

import { getAuthDestination } from "./authNavigation.js";

test("requires a two-factor step before navigating into the application", () => {
  assert.deepEqual(
    getAuthDestination({ two_factor_required: true, email: "member@example.test" }),
    { path: "/two-factor", state: { email: "member@example.test" } },
  );
});

test("navigates approved users to the dashboard", () => {
  assert.deepEqual(getAuthDestination({ access_token: "issued-token" }), {
    path: "/dashboard",
  });
});

test("sends new Google users to role selection without granting a session", () => {
  assert.deepEqual(
    getAuthDestination({
      success: false,
      existing_user: false,
      email: "new@example.test",
      name: "New User",
      registration_token: "short-lived-registration-token",
    }),
    {
      path: "/register",
      state: {
        method: "google",
        googleStep: 2,
        googleEmail: "new@example.test",
        googleName: "New User",
        googleRegToken: "short-lived-registration-token",
      },
    },
  );
});

test("does not grant a route for incomplete authentication responses", () => {
  assert.equal(getAuthDestination({ success: false }), null);
});
