export function createQrPayload(record) {
  if (typeof record?.encoded_value !== "string" || !record.encoded_value.trim()) {
    return null;
  }
  const raw = record.encoded_value.trim();

  // Rewrite pharmaverse:// custom-scheme URIs to navigable HTTP verification
  // URLs so that OS-level QR scanners (iOS Camera, Android Lens) land on the
  // verification page instead of producing a blank / unresolvable page.
  try {
    const u = new URL(raw);
    if (u.protocol === "pharmaverse:") {
      const origin =
        typeof window !== "undefined" ? window.location.origin : "";
      if (u.hostname === "verification") {
        // pharmaverse://verification?qr_id=QR-MED-000001
        // → http://localhost:5173/verification?qr_id=QR-MED-000001
        // Guard: a bare pharmaverse://verification with no search string has
        // no identifier — return null so the QR is shown as unavailable rather
        // than encoding a URL that opens /verification with a blank form.
        if (!u.search) return null;
        return `${origin}/verification${u.search}`;
      }
      if (u.hostname === "batch") {
        // pharmaverse://batch/BATCH-2026-000001
        // → http://localhost:5173/verification?batch_id=BATCH-2026-000001
        const batchId = decodeURIComponent(u.pathname.slice(1));
        return `${origin}/verification?batch_id=${encodeURIComponent(batchId)}`;
      }
    }
  } catch {
    // Not a parseable URL — fall through and return the raw value.
  }

  return raw;
}

export function parseQrPayload(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const payload = value.trim();

  // Direct identifiers: preserve the deterministic QR-MED-/BATCH-2026-… formats
  // and also accept other QR-… public ids (e.g. QR-TEST-0001).
  if (/^QR-[A-Z0-9][A-Z0-9-]*$/i.test(payload)) {
    return { qr_id: payload.toUpperCase() };
  }
  if (/^BATCH-2026-[0-9]{6}$/i.test(payload)) {
    return { batch_id: payload.toUpperCase() };
  }

  // Legacy encoded-value format: "BATCH-ID|DRUG-ID" (e.g. BATCH-TEST-001|DRUG-PARA-500).
  const legacy = /^([A-Za-z0-9][A-Za-z0-9_-]*)\|([A-Za-z0-9][A-Za-z0-9_-]*)$/.exec(payload);
  if (legacy) {
    return {
      batch_id: legacy[1].toUpperCase(),
      drug_id: legacy[2].toUpperCase(),
    };
  }

  try {
    const url = new URL(payload, window.location.origin);
    const qrId = url.searchParams.get("qr_id");
    const batchId = url.searchParams.get("batch_id");
    if (qrId && /^QR-MED-[0-9]{6}$/i.test(qrId)) {
      return { qr_id: qrId.toUpperCase() };
    }
    if (batchId && /^BATCH-2026-[0-9]{6}$/i.test(batchId)) {
      return { batch_id: batchId.toUpperCase() };
    }
    if (url.protocol === "pharmaverse:" && url.hostname === "batch") {
      const pathBatchId = decodeURIComponent(url.pathname.slice(1));
      if (/^BATCH-2026-[0-9]{6}$/i.test(pathBatchId)) {
        return { batch_id: pathBatchId.toUpperCase() };
      }
    }
  } catch {
    return null;
  }

  return null;
}
