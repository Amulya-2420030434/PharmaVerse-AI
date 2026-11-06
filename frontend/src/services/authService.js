import api from "./api";

export const getStoredUser = () => {
  try {
    return JSON.parse(localStorage.getItem("user") || "null");
  } catch {
    return null;
  }
};

export const saveAuthSession = (payload = {}) => {
  if (payload.access_token) {
    localStorage.setItem("access_token", payload.access_token);
  }

  if (payload.user) {
    localStorage.setItem("user", JSON.stringify(payload.user));
  }
};

export const login = async (username, password) => {
  const formData = new URLSearchParams();
  formData.append("username", String(username).trim());
  formData.append("password", String(password));

  const response = await api.post("/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  if (response.data.two_factor_required) {
    return response.data;
  }

  saveAuthSession({ access_token: response.data.access_token });
  try {
    const user = await getCurrentUser();
    return { ...response.data, user };
  } catch {
    return response.data;
  }
};

export const loginWithGoogle = async (idToken) => {
  const response = await api.post("/auth/google/login", { id_token: idToken });
  if (response.data.two_factor_required) {
    return response.data;
  }
  if (response.data.access_token) {
    saveAuthSession({
      access_token: response.data.access_token,
      user: {
        id: response.data.user_id,
        email: response.data.email,
        username: response.data.name,
        role: response.data.role,
        status: response.data.status,
      },
    });
    try {
      const user = await getCurrentUser();
      return { ...response.data, user };
    } catch {
      return response.data;
    }
  }
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await api.get("/auth/me");
  const user = response.data;
  saveAuthSession({ user });
  return user;
};

export const logout = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
};

export const sendOtp = async (email, purpose = "registration") => {
  const response = await api.post("/auth/otp/send", { email, purpose });
  return response.data;
};

export const verifyOtp = async (email, otp, purpose = "registration") => {
  const response = await api.post("/auth/otp/verify", { email, otp, purpose });
  return response.data;
};

export const registerEmail = async (data) => {
  const response = await api.post("/auth/register/email", data);
  return response.data;
};

export const verifyGoogleToken = async (idToken) => {
  const response = await api.post("/auth/google/verify", { id_token: idToken });
  return response.data;
};

export const registerGoogle = async (data) => {
  const response = await api.post("/auth/register/google", data);
  return response.data;
};

export const linkGoogleAccount = async (idToken) => {
  const response = await api.post("/auth/google/link", { id_token: idToken });
  return response.data;
};

export const resetPassword = async (data) => {
  const response = await api.post("/auth/password-reset", data);
  return response.data;
};

export const sendEmailVerificationLink = async (email) => {
  const response = await api.post("/auth/email-verification/send", { email });
  return response.data;
};

export const confirmEmailVerification = async (token) => {
  const response = await api.post("/auth/email-verification/confirm", { token });
  return response.data;
};

export const forgotPassword = async (email) => {
  const response = await api.post("/auth/forgot-password", { email });
  return response.data;
};

export const resetPasswordWithLink = async (token, newPassword, confirmPassword) => {
  const response = await api.post("/auth/reset-password", {
    token,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
  return response.data;
};

export const verifyTwoFactor = async (email, otp) => {
  const response = await api.post("/auth/2fa/verify", { email, otp });
  saveAuthSession({ access_token: response.data.access_token });
  const user = await getCurrentUser();
  return { ...response.data, user };
};

export const setTwoFactorEnabled = async (enabled) => {
  const response = await api.patch("/auth/2fa", { enabled });
  return response.data;
};
