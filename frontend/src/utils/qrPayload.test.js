import assert from "node:assert/strict";
import test from "node:test";

import { createQrPayload, parseQrPayload } from "./qrPayload.js";

globalThis.window = { location: { origin: "http://localhost:5173" } };

test("parses direct QR and batch identifiers", () => {
  assert.deepEqual(parseQrPayload("QR-MED-000001"), { qr_id: "QR-MED-000001" });
  assert.deepEqual(parseQrPayload("BATCH-2026-000001"), { batch_id: "BATCH-2026-000001" });
});

test("parses the deterministic PharmaVerse batch payload", () => {
  assert.deepEqual(
    parseQrPayload("pharmaverse://batch/BATCH-2026-000001"),
    { batch_id: "BATCH-2026-000001" },
  );
});

test("parses the deterministic QR-identity verification payload", () => {
  assert.deepEqual(
    parseQrPayload("pharmaverse://verification?qr_id=QR-MED-000005"),
    { qr_id: "QR-MED-000005" },
  );
});

test("parses application verification URLs and rejects unknown QR contents", () => {
  assert.deepEqual(
    parseQrPayload("http://localhost:5173/verification?qr_id=QR-MED-000042"),
    { qr_id: "QR-MED-000042" },
  );
  assert.equal(parseQrPayload("https://example.com/unrelated"), null);
  assert.equal(parseQrPayload("not a QR payload"), null);
  assert.equal(parseQrPayload(""), null);
});

// ── createQrPayload ────────────────────────────────────────────────────────

test("createQrPayload rewrites pharmaverse://verification?qr_id=... to an HTTP URL", () => {
  const result = createQrPayload({
    encoded_value: "pharmaverse://verification?qr_id=QR-MED-000001",
  });
  assert.equal(result, "http://localhost:5173/verification?qr_id=QR-MED-000001");
});

test("createQrPayload returns null for a bare pharmaverse://verification with no query string", () => {
  // This is the old-screenshot case: the stored value has no qr_id, so encoding
  // it as a QR would produce /verification with no identifier — useless and
  // confusing.  Returning null makes the Identities page show "Encoded payload
  // unavailable" so the operator knows to update the record.
  const result = createQrPayload({ encoded_value: "pharmaverse://verification" });
  assert.equal(result, null);
});

test("createQrPayload rewrites pharmaverse://batch/BATCH-... to an HTTP verification URL", () => {
  const result = createQrPayload({
    encoded_value: "pharmaverse://batch/BATCH-2026-000001",
  });
  assert.equal(result, "http://localhost:5173/verification?batch_id=BATCH-2026-000001");
});

test("createQrPayload passes through an already-valid HTTP verification URL unchanged", () => {
  const url = "http://localhost:5173/verification?qr_id=QR-MED-000042";
  assert.equal(createQrPayload({ encoded_value: url }), url);
});

test("createQrPayload returns null for a missing or empty encoded_value", () => {
  assert.equal(createQrPayload({}), null);
  assert.equal(createQrPayload({ encoded_value: "" }), null);
  assert.equal(createQrPayload(null), null);
});

// ── Regression: legacy BATCH-ID|DRUG-ID and non-deterministic QR ids ────────

test("parses the legacy BATCH-ID|DRUG-ID encoded value", () => {
  assert.deepEqual(
    parseQrPayload("BATCH-TEST-001|DRUG-PARA-500"),
    { batch_id: "BATCH-TEST-001", drug_id: "DRUG-PARA-500" },
  );
  assert.deepEqual(
    parseQrPayload("batch-test-001|drug-para-500"),
    { batch_id: "BATCH-TEST-001", drug_id: "DRUG-PARA-500" },
  );
});

test("parses a direct QR identifier outside the deterministic format", () => {
  assert.deepEqual(parseQrPayload("QR-TEST-0001"), { qr_id: "QR-TEST-0001" });
  assert.deepEqual(parseQrPayload("QR-MED-000001"), { qr_id: "QR-MED-000001" });
});

test("createQrPayload passes through a legacy BATCH-ID|DRUG-ID value", () => {
  assert.equal(
    createQrPayload({ encoded_value: "BATCH-TEST-001|DRUG-PARA-500" }),
    "BATCH-TEST-001|DRUG-PARA-500",
  );
});

test("rejects a legacy value that is missing one side", () => {
  assert.equal(parseQrPayload("BATCH-TEST-001|"), null);
  assert.equal(parseQrPayload("|DRUG-PARA-500"), null);
  assert.equal(parseQrPayload("BATCH-TEST-001"), null);
});
