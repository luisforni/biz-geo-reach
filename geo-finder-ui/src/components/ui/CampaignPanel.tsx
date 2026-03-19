import { useState, useMemo } from "react";
import { useCommerceStore } from "@/store/useCommerceStore";
import type { Commerce } from "@/types";

interface PanelContact {
  osmId: number;
  name: string;
  phone: string;
  hasPhone: boolean;
  subcategory: string;
  address: string;
  website: string;
}

interface CampaignForm {
  name: string;
  description: string;
  systemPrompt: string;
  autoSales: boolean;
  waitHours: number;
  maxMessages: number;
}

interface IngestResult {
  total_rows: number;
  contacts_loaded: number;
  contacts_no_phone: number;
  contacts_duplicate: number;
}

type Step = "config" | "creating" | "ingesting" | "done" | "error";

const DEFAULT_PROMPT =
  `Eres un asesor comercial digital especializado en servicios web para hostelería.
Tu objetivo es ayudar a bares y restaurantes a conseguir más clientes ofreciendo páginas web profesionales con menú digital integrado.

SERVICIO:
- Página web profesional con menú digital actualizable
- Menú QR para las mesas
- Alta en Google Maps y SEO local
- Desde 49€/mes o pago único desde 490€

INSTRUCCIONES:
1. Sé directo y personalizado, usa el nombre del negocio
2. Menciona un beneficio concreto para su tipo de local
3. Tono cercano y profesional (como WhatsApp entre conocidos)
4. Máximo 2 emojis
5. En modo auto: guía la conversación hacia concertar una llamada de 15 minutos`;

function normalizePhone(raw: string): string {
  const first = raw.split(/[;,]/)[0]?.trim() ?? "";
  const digits = first.replace(/[\s\-\.\(\)]/g, "");
  if (!digits) return "";
  if (digits.startsWith("+")) return digits;
  if (digits.startsWith("00")) return "+" + digits.slice(2);
  if (digits.length === 9 && /^[6789]/.test(digits)) return "+34" + digits;
  if (digits.length === 11 && digits.startsWith("34")) return "+" + digits;
  return digits;
}

function buildContact(item: Commerce): PanelContact {
  const raw =
    item.tags["phone"] ??
    item.tags["contact:phone"] ??
    item.tags["mobile"] ??
    item.tags["contact:mobile"] ??
    "";
  const phone = normalizePhone(raw);
  const street = [item.tags["addr:street"], item.tags["addr:housenumber"]]
    .filter(Boolean)
    .join(" ");
  const city = item.tags["addr:city"] ?? item.tags["addr:suburb"] ?? "";
  const address = [street, city].filter(Boolean).join(", ");
  return {
    osmId: item.osmId,
    name: item.name || "(sin nombre)",
    phone,
    hasPhone: phone.length > 0,
    subcategory: item.subcategory,
    address,
    website: item.tags["website"] ?? item.tags["contact:website"] ?? "",
  };
}

function escapeCell(val: string): string {
  if (val.includes(",") || val.includes('"') || val.includes("\n")) {
    return `"${val.replace(/"/g, '""')}"`;
  }
  return val;
}

function buildCsv(contacts: PanelContact[]): string {
  const headers = ["Nombre", "Teléfono", "Subcategoría", "Dirección", "Web"];
  const rows = contacts.map((c) => [
    c.name,
    c.phone,
    c.subcategory,
    c.address,
    c.website,
  ]);
  return (
    "\uFEFF" +
    [headers, ...rows].map((r) => r.map(escapeCell).join(",")).join("\n")
  );
}

export function CampaignPanel() {
  const { showCampaignPanel, campaignContacts, setShowCampaignPanel } =
    useCommerceStore();

  const contacts = useMemo(
    () => campaignContacts.map(buildContact),
    [campaignContacts],
  );

  const [form, setForm] = useState<CampaignForm>({
    name: "",
    description: "",
    systemPrompt: DEFAULT_PROMPT,
    autoSales: true,
    waitHours: 24,
    maxMessages: 5,
  });

  function apiUrl(): string {
    return localStorage.getItem("wa_ingestion_url") ?? "http://localhost:8010";
  }
  function authHeaders(): HeadersInit {
    const key = localStorage.getItem("wa_api_key") ?? "";
    return key ? { "X-API-Key": key } : {};
  }

  const withPhone = useMemo(
    () => contacts.filter((c) => c.hasPhone),
    [contacts],
  );
  const withoutCount = contacts.length - withPhone.length;

  const [step, setStep] = useState<Step>("config");
  const [campaignId, setCampaignId] = useState<number | null>(null);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!showCampaignPanel) return null;

  const busy = step === "creating" || step === "ingesting";

  function close() {
    setShowCampaignPanel(false);
    setStep("config");
    setResult(null);
    setError(null);
    setCampaignId(null);
  }

  async function submit() {
    if (!form.name.trim() || withPhone.length === 0) return;
    setStep("creating");
    setError(null);
    try {
      const resp1 = await fetch(`${apiUrl()}/api/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          name: form.name.trim(),
          description: form.description.trim() || null,
          system_prompt: form.systemPrompt,
          auto_sales_enabled: form.autoSales,
          wait_hours_no_reply: form.waitHours,
          max_auto_messages: form.maxMessages,
        }),
      });
      if (!resp1.ok) throw new Error(`Campaign: ${resp1.statusText}`);
      const data1 = (await resp1.json()) as { id: number };
      setCampaignId(data1.id);

      setStep("ingesting");
      const csv = buildCsv(withPhone);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const fd = new FormData();
      fd.append("file", blob, "comercios.csv");
      const resp2 = await fetch(
        `${apiUrl()}/api/campaigns/${data1.id}/ingest`,
        { method: "POST", headers: authHeaders(), body: fd },
      );
      if (!resp2.ok) throw new Error(`Ingest: ${resp2.statusText}`);
      const data2 = (await resp2.json()) as IngestResult;
      setResult(data2);
      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
      setStep("error");
    }
  }

  async function startCampaign() {
    if (!campaignId) return;
    try {
      const resp = await fetch(
        `${apiUrl()}/api/campaigns/${campaignId}/start`,
        { method: "POST", headers: authHeaders() },
      );
      if (!resp.ok) throw new Error(resp.statusText);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al iniciar");
    }
  }

  return (
    <div className="cp-overlay">
      <div className="cp-header">
        <button className="cp-back" onClick={close}>
          ← Volver
        </button>
        <div className="cp-header__title">WhatsApp Campaign</div>
        <div className="cp-header__stats">
          <span className="cp-pill cp-pill--green">{withPhone.length} con teléfono</span>
          <span className="cp-pill cp-pill--muted">{withoutCount} sin teléfono</span>
        </div>
      </div>

      <div className="cp-body">
        {step === "done" && result ? (
          <div className="cp-done">
            <div className="cp-done__icon">✓</div>
            <div className="cp-done__title">
              Campaña #{campaignId} creada con éxito
            </div>
            <div className="cp-ingest-grid">
              <div className="cp-ingest-stat">
                <div className="cp-ingest-stat__val">{result.total_rows}</div>
                <div className="cp-ingest-stat__label">Total filas</div>
              </div>
              <div className="cp-ingest-stat">
                <div className="cp-ingest-stat__val cp-ingest-stat__val--green">
                  {result.contacts_loaded}
                </div>
                <div className="cp-ingest-stat__label">Importados</div>
              </div>
              <div className="cp-ingest-stat">
                <div className="cp-ingest-stat__val cp-ingest-stat__val--muted">
                  {result.contacts_no_phone}
                </div>
                <div className="cp-ingest-stat__label">Sin teléfono</div>
              </div>
              <div className="cp-ingest-stat">
                <div className="cp-ingest-stat__val cp-ingest-stat__val--yellow">
                  {result.contacts_duplicate}
                </div>
                <div className="cp-ingest-stat__label">Duplicados</div>
              </div>
            </div>
            {error && <div className="cp-error">{error}</div>}
            <div className="cp-done__actions">
              <button className="cp-btn cp-btn--primary" onClick={startCampaign}>
                ▶ Iniciar campaña
              </button>
              <button className="cp-btn cp-btn--secondary" onClick={close}>
                Cerrar
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="cp-card">
              <div className="cp-card__title">01 — Configuración</div>
              <div className="cp-form-grid">
                <div className="cp-form-group">
                  <label className="cp-label">Nombre de la campaña *</label>
                  <input
                    className="cp-input"
                    type="text"
                    value={form.name}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, name: e.target.value }))
                    }
                    placeholder="Ej: Restaurantes Madrid Marzo 2026"
                    disabled={busy}
                  />
                </div>
                <div className="cp-form-group">
                  <label className="cp-label">Descripción (opcional)</label>
                  <input
                    className="cp-input"
                    type="text"
                    value={form.description}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, description: e.target.value }))
                    }
                    placeholder="Notas internas"
                    disabled={busy}
                  />
                </div>
                <div className="cp-form-group cp-form-group--full">
                  <label className="cp-label">System prompt (instrucciones para la IA)</label>
                  <textarea
                    className="cp-textarea"
                    value={form.systemPrompt}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, systemPrompt: e.target.value }))
                    }
                    disabled={busy}
                    rows={8}
                  />
                </div>
                <div className="cp-toggle-row cp-form-group--full">
                  <div>
                    <div className="cp-toggle-label">Venta automática</div>
                    <div className="cp-toggle-desc">
                      La IA continúa la conversación y pacta llamadas automáticamente
                    </div>
                  </div>
                  <label className="cp-switch">
                    <input
                      type="checkbox"
                      checked={form.autoSales}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, autoSales: e.target.checked }))
                      }
                      disabled={busy}
                    />
                    <span className="cp-switch__slider" />
                  </label>
                </div>
                <div className="cp-form-group">
                  <label className="cp-label">Horas sin respuesta (timeout)</label>
                  <input
                    className="cp-input"
                    type="number"
                    min={1}
                    max={168}
                    value={form.waitHours}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        waitHours: parseInt(e.target.value) || 24,
                      }))
                    }
                    disabled={busy}
                  />
                </div>
                <div className="cp-form-group">
                  <label className="cp-label">Máx. mensajes automáticos</label>
                  <input
                    className="cp-input"
                    type="number"
                    min={1}
                    max={20}
                    value={form.maxMessages}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        maxMessages: parseInt(e.target.value) || 5,
                      }))
                    }
                    disabled={busy}
                  />
                </div>
              </div>
            </div>

            <div className="cp-card">
              <div className="cp-card__title">
                02 — Contactos ({withPhone.length}
                {withoutCount > 0 && (
                  <span className="cp-dim" style={{ fontWeight: 400 }}>
                    {" "}· {withoutCount} sin teléfono omitidos
                  </span>
                )}
                )
              </div>
              <div className="cp-table-wrap">
                <table className="cp-table">
                  <thead>
                    <tr>
                      <th>Nombre</th>
                      <th>Teléfono</th>
                      <th>Tipo</th>
                      <th>Dirección</th>
                    </tr>
                  </thead>
                  <tbody>
                    {withPhone.map((c) => (
                      <tr key={c.osmId}>
                        <td>{c.name}</td>
                        <td className="cp-mono">{c.phone}</td>
                        <td>{c.subcategory}</td>
                        <td className="cp-dim">{c.address || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {(step === "error" || error) && (
              <div className="cp-error">{error}</div>
            )}

            <div className="cp-footer">
              <button
                className="cp-btn cp-btn--secondary"
                onClick={close}
                disabled={busy}
              >
                Cancelar
              </button>
              <button
                className="cp-btn cp-btn--primary"
                onClick={submit}
                disabled={busy || !form.name.trim() || withPhone.length === 0}
              >
                {step === "creating"
                  ? "⏳ Creando campaña..."
                  : step === "ingesting"
                    ? `⏳ Importando ${withPhone.length} contactos...`
                    : `⚡ Crear campaña · ${withPhone.length} contactos`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
