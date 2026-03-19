import React, { useState, useEffect, useCallback, useRef } from "react";
import { useCommerceStore } from "@/store/useCommerceStore";

interface CampaignRecord {
  id: number;
  name: string;
  description?: string | null;
  status: "draft" | "active" | "paused" | "completed" | "error";
  auto_sales_enabled: boolean;
  wait_hours_no_reply: number;
  max_auto_messages: number;
  created_at?: string;
  total_contacts?: number;
  contacts_by_state?: Record<string, number>;
}

interface ContactRecord {
  id: number;
  campaign_id: number;
  commerce_name: string;
  phone_raw: string;
  phone_normalized: string | null;
  state: string;
  first_message_sent_at: string | null;
  last_activity_at: string | null;
  notes: string | null;
  manual_mode: boolean;
  created_at: string;
}

interface ConversationMessage {
  role: "user" | "assistant" | "operator";
  content: string;
  timestamp: string;
}

interface WaStatus {
  connectionState: "connected" | "connecting" | "disconnected";
  hasQr: boolean;
}

type TopTab = "campaigns" | "whatsapp";
type View = "list" | "detail" | "conversation";

const CAMPAIGN_STATUS_LABEL: Record<string, string> = {
  draft: "Borrador", active: "Activa", paused: "Pausada",
  completed: "Finalizada", error: "Error",
};
const CAMPAIGN_STATUS_CLASS: Record<string, string> = {
  draft: "cm-badge--muted", active: "cm-badge--green", paused: "cm-badge--yellow",
  completed: "cm-badge--blue", error: "cm-badge--red",
};

const CONTACT_STATE_LABEL: Record<string, string> = {
  pending: "Pendiente",
  validating_whatsapp: "Verificando WA",
  no_whatsapp: "Sin WhatsApp",
  sending_first_message: "Enviando...",
  waiting_response: "Esperando resp.",
  timed_out: "Sin respuesta",
  in_conversation: "En conversación",
  scheduled_call: "Llamada pactada",
  rejected: "Rechazado",
  completed: "Completado",
  error: "Error",
};
const CONTACT_STATE_CLASS: Record<string, string> = {
  pending: "cm-badge--muted",
  validating_whatsapp: "cm-badge--yellow",
  no_whatsapp: "cm-badge--muted",
  sending_first_message: "cm-badge--yellow",
  waiting_response: "cm-badge--blue",
  timed_out: "cm-badge--muted",
  in_conversation: "cm-badge--green",
  scheduled_call: "cm-badge--blue",
  rejected: "cm-badge--red",
  completed: "cm-badge--blue",
  error: "cm-badge--red",
};

const AI_ACTIVE_STATES = new Set(["waiting_response", "in_conversation"]);

const WA_STATE_LABEL: Record<string, string> = {
  connected: "Conectado", connecting: "Conectando...", disconnected: "Desconectado",
};
const WA_STATE_CLASS: Record<string, string> = {
  connected: "cm-badge--green", connecting: "cm-badge--yellow", disconnected: "cm-badge--red",
};

function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}
function formatTime(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short" }) + " " +
    d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

export function CampaignsManager() {
  const { showCampaignsManager, setShowCampaignsManager, results, openCampaignPanel } =
    useCommerceStore();

  const [topTab, setTopTab] = useState<TopTab>("campaigns");
  const [view, setView] = useState<View>("list");

  const [campaignUrl, setCampaignUrl] = useState(
    () => localStorage.getItem("wa_ingestion_url") ?? "http://localhost:8010",
  );
  const [campaignKey, setCampaignKey] = useState(
    () => localStorage.getItem("wa_api_key") ?? "",
  );
  const [gatewayUrl, setGatewayUrl] = useState(
    () => localStorage.getItem("wa_gateway_url") ?? "http://localhost:3003",
  );
  const [gatewayKey, setGatewayKey] = useState(
    () => localStorage.getItem("wa_gateway_key") ?? "",
  );
  const [settingsSaved, setSettingsSaved] = useState(false);

  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<number | null>(null);

  const [selectedCampaign, setSelectedCampaign] = useState<CampaignRecord | null>(null);
  const [contacts, setContacts] = useState<ContactRecord[]>([]);
  const [contactsLoading, setContactsLoading] = useState(false);

  const [selectedContact, setSelectedContact] = useState<ContactRecord | null>(null);
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [convLoading, setConvLoading] = useState(false);
  const [msgInput, setMsgInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const [waStatus, setWaStatus] = useState<WaStatus | null>(null);
  const [waLoading, setWaLoading] = useState(false);
  const [waError, setWaError] = useState<string | null>(null);

  const campaignHeaders = useCallback(
    (): HeadersInit => (campaignKey ? { "X-API-Key": campaignKey } : {}),
    [campaignKey],
  );
  const gatewayHeaders = useCallback(
    (): HeadersInit => (gatewayKey ? { "X-API-Key": gatewayKey } : {}),
    [gatewayKey],
  );

  const fetchCampaigns = useCallback(async () => {
    setCampaignsLoading(true);
    setCampaignsError(null);
    try {
      const r = await fetch(`${campaignUrl}/api/campaigns`, { headers: campaignHeaders() });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const data = await r.json();
      setCampaigns(Array.isArray(data) ? data : (data.items ?? []));
    } catch (e) {
      setCampaignsError(e instanceof Error ? e.message : "Error al cargar");
    } finally {
      setCampaignsLoading(false);
    }
  }, [campaignUrl, campaignHeaders]);

  const fetchContacts = useCallback(async (campaignId: number) => {
    setContactsLoading(true);
    try {
      const r = await fetch(`${campaignUrl}/api/campaigns/${campaignId}/contacts`, {
        headers: campaignHeaders(),
      });
      if (!r.ok) throw new Error(r.statusText);
      setContacts(await r.json());
    } catch {
      setContacts([]);
    } finally {
      setContactsLoading(false);
    }
  }, [campaignUrl, campaignHeaders]);

  const fetchConversation = useCallback(async (campaignId: number, contactId: number) => {
    setConvLoading(true);
    try {
      const r = await fetch(
        `${campaignUrl}/api/campaigns/${campaignId}/contacts/${contactId}/conversation`,
        { headers: campaignHeaders() },
      );
      if (!r.ok) throw new Error(r.statusText);
      const data = await r.json();
      setConversation(data.messages ?? []);
    } catch {
      setConversation([]);
    } finally {
      setConvLoading(false);
    }
  }, [campaignUrl, campaignHeaders]);

  const fetchWaStatus = useCallback(async () => {
    setWaLoading(true);
    setWaError(null);
    try {
      const r = await fetch(`${gatewayUrl}/phone/state`, { headers: gatewayHeaders() });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      setWaStatus(await r.json());
    } catch (e) {
      setWaError(e instanceof Error ? e.message : "Sin conexión al gateway");
      setWaStatus(null);
    } finally {
      setWaLoading(false);
    }
  }, [gatewayUrl, gatewayHeaders]);

  useEffect(() => {
    if (!showCampaignsManager) return;
    if (topTab === "campaigns" && view === "list") fetchCampaigns();
    if (topTab === "whatsapp") fetchWaStatus();
  }, [showCampaignsManager, topTab, view, fetchCampaigns, fetchWaStatus]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation]);

  if (!showCampaignsManager) return null;

  function close() {
    setShowCampaignsManager(false);
    setView("list");
    setTopTab("campaigns");
    setSelectedCampaign(null);
    setSelectedContact(null);
  }

  function saveSettings() {
    localStorage.setItem("wa_ingestion_url", campaignUrl);
    localStorage.setItem("wa_api_key", campaignKey);
    localStorage.setItem("wa_gateway_url", gatewayUrl);
    localStorage.setItem("wa_gateway_key", gatewayKey);
    setSettingsSaved(true);
    setTimeout(() => setSettingsSaved(false), 2000);
    fetchCampaigns();
    fetchWaStatus();
  }

  async function startCampaign(id: number) {
    setActionBusy(id);
    try {
      const r = await fetch(`${campaignUrl}/api/campaigns/${id}/start`, {
        method: "POST", headers: campaignHeaders(),
      });
      if (!r.ok) throw new Error(r.statusText);
      await fetchCampaigns();
    } catch (e) {
      setCampaignsError(e instanceof Error ? e.message : "Error al iniciar");
    } finally {
      setActionBusy(null);
    }
  }

  async function pauseCampaign(id: number) {
    setActionBusy(id);
    try {
      const r = await fetch(`${campaignUrl}/api/campaigns/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...campaignHeaders() },
        body: JSON.stringify({ status: "paused" }),
      });
      if (!r.ok) throw new Error(r.statusText);
      await fetchCampaigns();
    } catch (e) {
      setCampaignsError(e instanceof Error ? e.message : "Error al pausar");
    } finally {
      setActionBusy(null);
    }
  }

  async function openDetail(campaign: CampaignRecord) {
    setSelectedCampaign(campaign);
    setView("detail");
    await fetchContacts(campaign.id);
  }

  async function openConversation(contact: ContactRecord) {
    setSelectedContact(contact);
    setView("conversation");
    setSendError(null);
    setMsgInput("");
    if (selectedCampaign) {
      await fetchConversation(selectedCampaign.id, contact.id);
    }
  }

  async function toggleManualMode(contact: ContactRecord) {
    const newMode = !contact.manual_mode;
    try {
      const r = await fetch(
        `${campaignUrl}/api/campaigns/${contact.campaign_id}/contacts/${contact.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json", ...campaignHeaders() },
          body: JSON.stringify({ manual_mode: newMode }),
        },
      );
      if (!r.ok) throw new Error(r.statusText);
      setContacts((cs) => cs.map((c) => c.id === contact.id ? { ...c, manual_mode: newMode } : c));
      if (selectedContact?.id === contact.id) {
        setSelectedContact((c) => c ? { ...c, manual_mode: newMode } : c);
      }
    } catch {
    }
  }

  async function sendMessage() {
    if (!msgInput.trim() || !selectedContact || !selectedCampaign || sending) return;
    setSending(true);
    setSendError(null);
    const text = msgInput.trim();
    setMsgInput("");
    try {
      const r = await fetch(
        `${campaignUrl}/api/campaigns/${selectedCampaign.id}/contacts/${selectedContact.id}/send`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", ...campaignHeaders() },
          body: JSON.stringify({ message: text }),
        },
      );
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail ?? r.statusText);
      }
      setConversation((prev) => [
        ...prev,
        { role: "operator", content: text, timestamp: new Date().toISOString() },
      ]);
      setSelectedContact((c) => c ? { ...c, manual_mode: true } : c);
      setContacts((cs) =>
        cs.map((c) => c.id === selectedContact.id ? { ...c, manual_mode: true } : c),
      );
    } catch (e) {
      setSendError(e instanceof Error ? e.message : "Error al enviar");
      setMsgInput(text);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const headerTitle =
    view === "conversation" && selectedContact
      ? selectedContact.commerce_name
      : view === "detail" && selectedCampaign
      ? selectedCampaign.name
      : "WhatsApp Campaigns";

  return (
    <div className="cp-overlay">
      <div className="cp-header">
        <button
          className="cp-back"
          onClick={() => {
            if (view === "conversation") { setView("detail"); setSelectedContact(null); }
            else if (view === "detail") { setView("list"); setSelectedCampaign(null); }
            else close();
          }}
        >
          ← {view === "list" ? "Volver" : "Atrás"}
        </button>

        <div className="cp-header__title" style={{ fontSize: view === "detail" || view === "conversation" ? 13 : 14 }}>
          {headerTitle}
        </div>

        {view === "list" && (
          <div className="cm-tabs">
            <button
              className={`cm-tab ${topTab === "campaigns" ? "cm-tab--active" : ""}`}
              onClick={() => setTopTab("campaigns")}
            >
              Campañas
            </button>
            <button
              className={`cm-tab ${topTab === "whatsapp" ? "cm-tab--active" : ""}`}
              onClick={() => { setTopTab("whatsapp"); fetchWaStatus(); }}
            >
              WhatsApp
              {waStatus && (
                <span className={`cm-tab-dot cm-tab-dot--${waStatus.connectionState}`} />
              )}
            </button>
          </div>
        )}

        {view === "detail" && selectedCampaign && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className={`cm-badge ${CAMPAIGN_STATUS_CLASS[selectedCampaign.status] ?? "cm-badge--muted"}`}>
              {CAMPAIGN_STATUS_LABEL[selectedCampaign.status] ?? selectedCampaign.status}
            </span>
            <button
              className="cp-btn cp-btn--secondary"
              style={{ padding: "4px 10px", fontSize: 11 }}
              onClick={() => fetchContacts(selectedCampaign.id)}
              disabled={contactsLoading}
            >
              ↻
            </button>
          </div>
        )}

        {view === "conversation" && selectedContact && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className={`cm-badge ${CONTACT_STATE_CLASS[selectedContact.state] ?? "cm-badge--muted"}`}>
              {CONTACT_STATE_LABEL[selectedContact.state] ?? selectedContact.state}
            </span>
            <span
              className={`cm-badge ${selectedContact.manual_mode ? "cm-badge--yellow" : "cm-badge--green"}`}
              title={selectedContact.manual_mode ? "Modo manual activo" : "IA respondiendo automáticamente"}
            >
              {selectedContact.manual_mode ? "Manual" : "IA activa"}
            </span>
          </div>
        )}
      </div>

      {view === "list" && topTab === "campaigns" && (
        <div className="cp-body">
          <div className="cm-toolbar">
            <button className="cp-btn cp-btn--primary" onClick={() => { setShowCampaignsManager(false); openCampaignPanel(results); }}>
              + Nueva campaña
              {results.length > 0 && (
                <span className="cm-contacts-badge">{results.length} contactos</span>
              )}
            </button>
            <button className="cp-btn cp-btn--secondary" onClick={fetchCampaigns} disabled={campaignsLoading}>
              {campaignsLoading ? "⏳" : "↻ Actualizar"}
            </button>
          </div>

          {campaignsError && <div className="cp-error">{campaignsError}</div>}

          <div className="cp-card">
            <div className="cp-card__title">Campañas</div>
            {campaignsLoading && campaigns.length === 0 ? (
              <div className="cm-empty">Cargando...</div>
            ) : campaigns.length === 0 ? (
              <div className="cm-empty">
                Sin campañas.{" "}
                <button className="cm-link" onClick={() => { setShowCampaignsManager(false); openCampaignPanel(results); }}>
                  Crea la primera.
                </button>
              </div>
            ) : (
              <div className="cp-table-wrap">
                <table className="cp-table">
                  <thead>
                    <tr>
                      <th>#</th><th>Nombre</th><th>Estado</th>
                      <th>Contactos</th><th>Creada</th><th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {campaigns.map((c) => (
                      <tr key={c.id} className="cm-row-clickable" onClick={() => openDetail(c)}>
                        <td className="cp-mono">{c.id}</td>
                        <td>
                          <div style={{ fontWeight: 500, color: "#e2e8f0" }}>{c.name}</div>
                          {c.description && <div className="cp-dim" style={{ fontSize: 11 }}>{c.description}</div>}
                        </td>
                        <td>
                          <span className={`cm-badge ${CAMPAIGN_STATUS_CLASS[c.status] ?? "cm-badge--muted"}`}>
                            {CAMPAIGN_STATUS_LABEL[c.status] ?? c.status}
                          </span>
                        </td>
                        <td className="cp-dim">{c.total_contacts ?? "—"}</td>
                        <td className="cp-dim">{formatDate(c.created_at)}</td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="cm-actions">
                            {(c.status === "draft" || c.status === "paused") && (
                              <button className="cm-action-btn cm-action-btn--start"
                                onClick={() => startCampaign(c.id)} disabled={actionBusy === c.id}>
                                {actionBusy === c.id ? "..." : "▶ Iniciar"}
                              </button>
                            )}
                            {c.status === "active" && (
                              <button className="cm-action-btn cm-action-btn--pause"
                                onClick={() => pauseCampaign(c.id)} disabled={actionBusy === c.id}>
                                {actionBusy === c.id ? "..." : "⏸ Pausar"}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {view === "list" && topTab === "whatsapp" && (
        <div className="cp-body">
          <div className="cp-card">
            <div className="cp-card__title">Estado de la conexión</div>
            <div className="cm-wa-status-block">
              {waLoading ? (
                <span className="cp-dim">Consultando gateway...</span>
              ) : waError ? (
                <div className="cm-wa-status-row">
                  <span className="cm-badge cm-badge--red">Sin conexión</span>
                  <span className="cp-dim" style={{ fontSize: 11 }}>{waError}</span>
                </div>
              ) : waStatus ? (
                <div className="cm-wa-status-row">
                  <span className={`cm-badge ${WA_STATE_CLASS[waStatus.connectionState]}`}>
                    {WA_STATE_LABEL[waStatus.connectionState]}
                  </span>
                  {waStatus.hasQr && (
                    <span className="cm-badge cm-badge--yellow">QR disponible — ver consola del gateway</span>
                  )}
                </div>
              ) : null}
              <button className="cp-btn cp-btn--secondary" onClick={fetchWaStatus} disabled={waLoading}
                style={{ marginTop: 8, alignSelf: "flex-start" }}>
                {waLoading ? "..." : "↻ Verificar"}
              </button>
            </div>
          </div>

          <div className="cp-card">
            <div className="cp-card__title">Campaign Service</div>
            <div className="cp-form-grid">
              <div className="cp-form-group">
                <label className="cp-label">URL</label>
                <input className="cp-input" type="text" value={campaignUrl}
                  onChange={(e) => setCampaignUrl(e.target.value)} placeholder="http://localhost:8010" />
              </div>
              <div className="cp-form-group">
                <label className="cp-label">API Key</label>
                <input className="cp-input" type="password" value={campaignKey}
                  onChange={(e) => setCampaignKey(e.target.value)} placeholder="X-API-Key" />
              </div>
            </div>
          </div>

          <div className="cp-card">
            <div className="cp-card__title">WhatsApp Gateway</div>
            <div className="cp-form-grid">
              <div className="cp-form-group">
                <label className="cp-label">URL</label>
                <input className="cp-input" type="text" value={gatewayUrl}
                  onChange={(e) => setGatewayUrl(e.target.value)} placeholder="http://localhost:3003" />
              </div>
              <div className="cp-form-group">
                <label className="cp-label">API Key</label>
                <input className="cp-input" type="password" value={gatewayKey}
                  onChange={(e) => setGatewayKey(e.target.value)} placeholder="X-API-Key" />
              </div>
            </div>
          </div>

          <div className="cp-footer">
            <button className="cp-btn cp-btn--primary" onClick={saveSettings}>
              {settingsSaved ? "✓ Guardado" : "Guardar configuración"}
            </button>
          </div>
        </div>
      )}

      {view === "detail" && selectedCampaign && (
        <div className="cp-body">
          {contactsLoading && contacts.length === 0 ? (
            <div className="cm-empty">Cargando contactos...</div>
          ) : contacts.length === 0 ? (
            <div className="cm-empty">Esta campaña no tiene contactos.</div>
          ) : (
            <div className="cp-card">
              <div className="cp-card__title">
                Contactos ({contacts.length})
              </div>
              <div className="cp-table-wrap">
                <table className="cp-table">
                  <thead>
                    <tr>
                      <th>Comercio</th><th>Teléfono</th><th>Estado</th>
                      <th>IA</th><th>Última actividad</th><th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contacts.map((c) => (
                      <tr key={c.id} className="cm-row-clickable" onClick={() => openConversation(c)}>
                        <td style={{ color: "#e2e8f0", fontWeight: 500 }}>{c.commerce_name}</td>
                        <td className="cp-mono">{c.phone_normalized ?? c.phone_raw}</td>
                        <td>
                          <span className={`cm-badge ${CONTACT_STATE_CLASS[c.state] ?? "cm-badge--muted"}`}>
                            {CONTACT_STATE_LABEL[c.state] ?? c.state}
                          </span>
                        </td>
                        <td>
                          <span className={`cm-badge ${c.manual_mode ? "cm-badge--muted" : "cm-badge--green"}`}
                            style={{ fontSize: 10 }}>
                            {c.manual_mode ? "Manual" : "IA"}
                          </span>
                        </td>
                        <td className="cp-dim" style={{ fontSize: 11 }}>
                          {formatTime(c.last_activity_at)}
                        </td>
                        <td onClick={(e) => e.stopPropagation()}>
                          {AI_ACTIVE_STATES.has(c.state) && (
                            <button
                              className={`cm-action-btn ${c.manual_mode ? "cm-action-btn--start" : "cm-action-btn--pause"}`}
                              onClick={() => toggleManualMode(c)}
                              title={c.manual_mode ? "Activar respuestas automáticas de IA" : "Detener IA y pasar a modo manual"}
                            >
                              {c.manual_mode ? "Activar IA" : "Detener IA"}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {view === "conversation" && selectedContact && (
        <div className="cm-chat-layout">
          <div className="cm-chat-body">
            {convLoading ? (
              <div className="cm-empty">Cargando conversación...</div>
            ) : conversation.length === 0 ? (
              <div className="cm-empty" style={{ margin: "auto" }}>Sin mensajes todavía.</div>
            ) : (
              conversation.map((msg, i) => (
                <div
                  key={i}
                  className={`cm-bubble cm-bubble--${msg.role}`}
                  title={formatTime(msg.timestamp)}
                >
                  {msg.role !== "user" && (
                    <div className="cm-bubble__role">
                      {msg.role === "operator" ? "Tú" : "IA"}
                    </div>
                  )}
                  <div className="cm-bubble__text">{msg.content}</div>
                  <div className="cm-bubble__time">{formatTime(msg.timestamp)}</div>
                </div>
              ))
            )}
            <div ref={chatEndRef} />
          </div>

          {selectedContact.manual_mode === false && AI_ACTIVE_STATES.has(selectedContact.state) && (
            <div className="cm-chat-ia-notice">
              <span className="cm-badge cm-badge--green">IA activa</span>
              <span className="cp-dim" style={{ fontSize: 12 }}>
                Enviar un mensaje aquí desactivará la IA automáticamente.
              </span>
              <button
                className="cm-action-btn cm-action-btn--pause"
                onClick={() => toggleManualMode(selectedContact)}
              >
                Detener IA
              </button>
            </div>
          )}

          {sendError && <div className="cp-error" style={{ margin: "0 24px 8px" }}>{sendError}</div>}

          <div className="cm-chat-footer">
            <textarea
              className="cm-chat-input"
              value={msgInput}
              onChange={(e) => setMsgInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe un mensaje… (Enter para enviar, Shift+Enter nueva línea)"
              disabled={sending}
            />
            <button
              className="cp-btn cp-btn--primary"
              onClick={sendMessage}
              disabled={sending || !msgInput.trim()}
              style={{ alignSelf: "flex-end" }}
            >
              {sending ? "..." : "Enviar"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
