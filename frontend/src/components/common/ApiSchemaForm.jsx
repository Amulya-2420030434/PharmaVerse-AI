import { useEffect, useMemo, useState } from "react";
import { LoaderCircle, Plus, X } from "lucide-react";

import api from "../../services/api";
import { extractErrorMessage } from "../../utils/error";

function apiConfig() {
  const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001/api";
  const parsed = new URL(base);
  return {
    root: base.replace(/\/api\/?$/, ""),
    prefix: parsed.pathname.replace(/\/$/, ""),
  };
}

async function loadOpenApi() {
  const response = await fetch(`${apiConfig().root}/openapi.json`);
  if (!response.ok) throw new Error(`Unable to load backend schema (${response.status}).`);
  return response.json();
}

function resolveSchema(schema, components) {
  if (!schema) return {};
  if (schema.$ref) {
    const ref = schema.$ref.split("/").pop();
    return components?.[ref] || {};
  }
  if (schema.allOf) {
    return schema.allOf.reduce((merged, item) => ({ ...merged, ...resolveSchema(item, components) }), {});
  }
  if (schema.oneOf?.length) return resolveSchema(schema.oneOf[0], components);
  if (schema.anyOf?.length) return resolveSchema(schema.anyOf[0], components);
  return schema;
}

function findOperation(openApi, method, path) {
  const methodKey = method.toLowerCase();
  const prefix = apiConfig().prefix;
  const candidatePaths = [path, `${prefix}${path}`].filter(Boolean);

  for (const candidatePath of candidatePaths) {
    const direct = openApi?.paths?.[candidatePath]?.[methodKey];
    if (direct) return { path: candidatePath, operation: direct };
  }

  const normalized = `${prefix}${path}`.replace(/\/?$/, "");
  const match = Object.entries(openApi?.paths || {}).find(([candidate, item]) => {
    const template = candidate.replace(/\{[^}]+\}/g, "[^/]+");
    return new RegExp(`^${template}/?$`).test(normalized) && item?.[methodKey];
  });

  return match ? { path: match[0], operation: match[1][methodKey] } : null;
}

function humanize(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function initialValue(property) {
  if (property?.default !== undefined) return property.default;
  if (property?.example !== undefined) return property.example;
  if (property?.examples && Array.isArray(property.examples) && property.examples[0] !== undefined) return property.examples[0];
  if (property?.enum?.length) return property.enum[0];
  if (property?.type === "boolean") return false;
  if (property?.type === "array" || property?.type === "object") return "";
  return "";
}

function fieldInputType(schema) {
  if (schema.enum?.length) return "select";
  if (schema.type === "boolean") return "checkbox";
  if (schema.type === "integer" || schema.type === "number") return "number";
  if (schema.format === "date-time") return "datetime-local";
  if (schema.format === "date") return "date";
  if (schema.type === "array" || schema.type === "object") return "json";
  return "text";
}

function coerceValue(raw, schema) {
  if (schema.type === "integer") return raw === "" ? null : Number.parseInt(raw, 10);
  if (schema.type === "number") return raw === "" ? null : Number(raw);
  if (schema.type === "boolean") return Boolean(raw);
  if (schema.type === "array" || schema.type === "object") {
    if (raw === "") return null;
    return JSON.parse(raw);
  }
  if (schema.format === "date-time" && raw) return new Date(raw).toISOString();
  return raw;
}

function displayValue(value, schema) {
  if (schema.type === "boolean") return Boolean(value);
  if (schema.type === "array" || schema.type === "object") return value ? JSON.stringify(value, null, 2) : "";
  if (schema.format === "date-time" && value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toISOString().slice(0, 16);
  }
  return value ?? "";
}

/* eslint-disable react-hooks/exhaustive-deps */
export default function ApiSchemaForm({
  endpoint,
  title,
  submitLabel = "Create",
  method = "POST",
  onSuccess,
  onClose,
  initialValues = {},
}) {
  const [schema, setSchema] = useState(null);
  const [fields, setFields] = useState([]);
  const [form, setForm] = useState({});
  const [schemaError, setSchemaError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const openApi = await loadOpenApi();
        const found = findOperation(openApi, method, endpoint);
        if (!found) throw new Error(`No ${method} operation found for ${endpoint}.`);

        const body = found.operation?.requestBody?.content?.["application/json"]?.schema
          || found.operation?.requestBody?.content?.["application/x-www-form-urlencoded"]?.schema;
        const resolved = resolveSchema(body, openApi.components?.schemas);
        const properties = resolved?.properties || {};
        const required = new Set(resolved?.required || []);

        const operationFields = Object.entries(properties)
          .map(([name, value]) => ({ name, schema: resolveSchema(value, openApi.components?.schemas), required: required.has(name) }))
          .filter(({ schema: fieldSchema }) => !fieldSchema.readOnly);

        const initial = {};
        operationFields.forEach(({ name, schema: fieldSchema }) => {
          initial[name] = displayValue(initialValues[name] ?? initialValue(fieldSchema), fieldSchema);
        });

        if (active) {
          setSchema(resolved);
          setFields(operationFields);
          setForm(initial);
        }
      } catch (error) {
        if (active) setSchemaError(error.message || "Unable to load form schema.");
      }
    })();

    return () => { active = false; };
  }, [endpoint, method, JSON.stringify(initialValues)]);

  const hasBody = useMemo(() => Boolean(schema && Object.keys(schema.properties || {}).length), [schema]);

  const updateField = (name, value) => setForm((current) => ({ ...current, [name]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError("");

    try {
      const payload = {};
      fields.forEach(({ name, schema: fieldSchema }) => {
        const raw = form[name];
        if (raw === "" || raw === null || raw === undefined) {
          if (fieldSchema.default !== undefined || !fieldSchema) return;
          return;
        }
        payload[name] = coerceValue(raw, fieldSchema);
      });

      const response = await api.request({ method, url: endpoint, data: hasBody ? payload : undefined });
      onSuccess?.(response.data);
      onClose?.();
    } catch (error) {
      setSubmitError(extractErrorMessage(error, "Unable to complete the request."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[#102a43]/40 p-4 sm:p-8">
      <div className="my-8 w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4 sm:px-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5a1725]">Operational action</p>
            <h2 className="mt-1 text-xl font-bold text-[#102a43]">{title}</h2>
            <p className="mt-1 text-xs text-slate-500">Using the live FastAPI OpenAPI contract for this operation.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Close dialog">
            <X size={18} />
          </button>
        </div>

        {schemaError ? (
          <div className="m-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{schemaError}</div>
        ) : !schema ? (
          <div className="flex items-center gap-2 p-8 text-sm text-slate-500"><LoaderCircle size={17} className="animate-spin" /> Loading backend form schema…</div>
        ) : (
          <form onSubmit={submit} className="space-y-5 p-5 sm:p-6">
            {fields.length === 0 ? (
              <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">This operation does not require a request body.</p>
            ) : fields.map(({ name, schema: fieldSchema, required }) => {
              const type = fieldInputType(fieldSchema);
              return (
                <label key={name} className="block text-sm font-medium text-slate-700">
                  <span>{humanize(name)}{required && <span className="ml-1 text-red-600">*</span>}</span>
                  {type === "select" ? (
                    <select value={form[name] ?? ""} onChange={(event) => updateField(name, event.target.value)} required={required} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-[#5a1725]">
                      {fieldSchema.enum.map((option) => <option key={String(option)} value={String(option)}>{String(option)}</option>)}
                    </select>
                  ) : type === "checkbox" ? (
                    <input type="checkbox" checked={Boolean(form[name])} onChange={(event) => updateField(name, event.target.checked)} className="ml-3 align-middle" />
                  ) : type === "json" ? (
                    <textarea value={form[name] ?? ""} onChange={(event) => updateField(name, event.target.value)} required={required} rows={5} placeholder='JSON value, e.g. ["item-1"]' className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 font-mono text-xs outline-none focus:border-[#5a1725]" />
                  ) : (
                    <input type={type} value={form[name] ?? ""} onChange={(event) => updateField(name, event.target.value)} required={required} step={fieldSchema.type === "number" ? "any" : undefined} className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-[#5a1725]" />
                  )}
                  {fieldSchema.description && <span className="mt-1 block text-xs font-normal leading-5 text-slate-500">{fieldSchema.description}</span>}
                </label>
              );
            })}

            {submitError && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{submitError}</div>}

            <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
              <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-slate-300">Cancel</button>
              <button type="submit" disabled={submitting} className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#5a1725] px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">
                {submitting ? <LoaderCircle size={16} className="animate-spin" /> : <Plus size={16} />}
                {submitting ? "Saving…" : submitLabel}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
