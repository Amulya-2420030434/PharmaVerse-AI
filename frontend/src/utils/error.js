export function extractErrorMessage(error, fallback = "Something went wrong.") {
  // Check standard PharmaVerse unified error envelope: { success: false, error: { code, message, details } }
  const apiError = error?.response?.data?.error;
  if (typeof apiError === "object" && apiError !== null) {
    if (typeof apiError.message === "string" && apiError.message.trim()) {
      return apiError.message.trim();
    }
    if (typeof apiError.details === "string" && apiError.details.trim()) {
      return apiError.details.trim();
    }
    if (Array.isArray(apiError.details) && apiError.details.length > 0) {
      return apiError.details
        .map((item) => item?.msg || item?.message || JSON.stringify(item))
        .join("; ");
    }
  }

  // Check direct FastAPI detail / message
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();

  const message = error?.response?.data?.message;
  if (typeof message === "string" && message.trim()) return message.trim();

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.loc?.join(".") || JSON.stringify(item))
      .join("; ");
  }

  const data = error?.response?.data;
  if (data && typeof data === "object") {
    const entries = Object.entries(data).filter(
      ([key, value]) => key !== "success" && value != null && value !== "" && typeof value !== "object",
    );
    if (entries.length > 0) {
      return entries.map(([key, value]) => `${key}: ${value}`).join("; ");
    }
  }

  if (typeof error?.message === "string" && error.message.trim()) return error.message.trim();
  return fallback;
}
