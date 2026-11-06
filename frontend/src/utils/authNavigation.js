export function getAuthDestination(response) {
  if (response?.two_factor_required) {
    return { path: "/two-factor", state: { email: response.email } };
  }
  if (response?.access_token) {
    return { path: "/dashboard" };
  }
  if (response?.existing_user === false && response.registration_token) {
    return {
      path: "/register",
      state: {
        method: "google",
        googleStep: 2,
        googleEmail: response.email,
        googleName: response.name,
        googleRegToken: response.registration_token,
      },
    };
  }
  return null;
}
