import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "../axiosConfig";
import ConversationTimeline from "../components/ConversationTimeline";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://127.0.0.1:8000";

export default function Inbox() {

  const [attachments, setAttachments] = useState([]);
  const [activeTab, setActiveTab] = useState("inbox");
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [search, setSearch] = useState("");

  const [accounts, setAccounts] = useState([]);
  const [syncStatuses, setSyncStatuses] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");

  const [showCompose, setShowCompose] = useState(false);
  const [composeData, setComposeData] = useState({
    to: "",
    subject: "",
    body: ""
  });

  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState("");
  const [error, setError] = useState("");
  const location = useLocation();
  // =========================
  // LOAD ACCOUNTS
  // =========================
  const loadAccounts = async () => {
    try {
      const res = await axios.get("/api/email-accounts/");
      setAccounts(res.data || []);
      if (res.data?.length > 0 && !selectedAccountId) {
        setSelectedAccountId(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadSyncStatus = async () => {
    try {
      const res = await axios.get("/api/inbox/sync-status/");
      setSyncStatuses(res.data || []);
    } catch (err) {
      console.error("Sync status error:", err);
    }
  };

  useEffect(() => {
    loadAccounts();
    loadSyncStatus();
  }, []);

  const getSyncStatus = (platform) => {
    return syncStatuses.find((item) => item.platform === platform);
  };

  const formatSyncStatus = (platform) => {
    const item = getSyncStatus(platform);
    if (!item) return "Not synced";

    const progress = item.status === "syncing" ? ` (${item.progress || 0}%)` : "";
    const lastSynced = item.last_synced_at
      ? ` | Last: ${new Date(item.last_synced_at).toLocaleString()}`
      : "";

    return `${item.status}${progress}${lastSynced}`;
  };

  // =========================
  // LOAD CONVERSATIONS
  // =========================
  const loadConversations = async () => {
    try {
      setError("");
      setLoading(true);
      const queryParams = new URLSearchParams({
        folder: activeTab,
      });

      if (search.trim()) {
        queryParams.set("search", search.trim());
      }

      if (selectedAccountId) {
        queryParams.set("account_id", selectedAccountId);
      }

      const res = await axios.get(`/api/inbox/unified-conversations/?${queryParams.toString()}`);
      const data = res.data.results || [];
      setConversations(data);
      // ✅ auto open first email
      const urlParams = new URLSearchParams(location.search);
      const conversationFromUrl = urlParams.get("conversation");

      if (data.length > 0) {
        if (conversationFromUrl) {
          const match = data.find(
            (conv) => String(conv.conversation_id) === String(conversationFromUrl)
          );

          if (match) {
            setSelectedId(match.conversation_id);
          } else if (!selectedId) {
            setSelectedId(data[0].conversation_id);
          }
        } else if (!selectedId) {
          setSelectedId(data[0].conversation_id);
        }
      }
    } catch (err) {
      console.error("Load error:", err);
      setError("Unable to load conversations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
  setSelectedId(null);     
  setMessages([]);         
  loadConversations();
}, [activeTab, location.search, search, selectedAccountId]);

  // =========================
  // REALTIME WEBSOCKET 🔥
  // =========================
  useEffect(() => {

    const token = localStorage.getItem("access");

    if (!token) return;

    const socket = new WebSocket(`${WS_BASE_URL}/ws/inbox/?token=${token}`);

    socket.onopen = () => {
      console.log("WS Connected ✅");
    };

    socket.onmessage = (event) => {
      console.log("Realtime update:", event.data);
      loadConversations();
    };

    socket.onerror = (err) => {
      console.error("WS Error ❌", err);
    };

    socket.onclose = () => {
      console.log("WS Closed ❌");
    };

    return () => socket.close();

  }, []);

  // =========================
  // LOAD THREAD
  // =========================
  useEffect(() => {
    if (!selectedId) return;

    console.log("📩 Loading conversation:", selectedId);

    axios.get(`/api/inbox/conversations/${selectedId}/`)
      .then(res => {
        console.log("THREAD API:", res.data);

        setMessages(res.data.messages || []);
        setAttachments(res.data.attachments || []);

        axios.post(`/api/inbox/conversation/${selectedId}/mark-read/`)
          .then(() => {
            setConversations((items) =>
              items.map((item) =>
                item.conversation_id === selectedId
                  ? { ...item, unread_count: 0 }
                  : item
              )
            );
          })
          .catch((err) => {
            console.error("Mark read error:", err);
          });
      })
      .catch(err => {
        console.error("❌ Thread load error:", err);
        setMessages([]);
        setAttachments([]);
      });

  }, [selectedId]);

  // =========================
  // SEND EMAIL
  // =========================
  const sendEmail = async () => {
    try {
      await axios.post("/api/inbox/send/", {
        to: composeData.to,
        subject: composeData.subject,
        body: composeData.body,
        account_id: selectedAccountId,
      });

      setShowCompose(false);
      setComposeData({ to: "", subject: "", body: "" });

      setActiveTab("sent");
      loadConversations();

    } catch (err) {
      console.error(err);
      alert("Send failed ❌");
    }
  };

  // =========================
  // SAVE DRAFT
  // =========================
  const saveDraft = async () => {
    try {

      await axios.post("/api/inbox/draft/save/", {
        conversation_id: selectedId,
        subject: composeData.subject,
        body: composeData.body,
        recipients: composeData.to,
        account_id: selectedAccountId,
      });

      setShowCompose(false);
      setActiveTab("draft");
      loadConversations();

    } catch (err) {
      console.error(err);
      alert("Draft failed ❌");
    }
  };
  const syncProvider = async (provider) => {
    const endpoint =
      provider === "gmail"
        ? "/api/google/oauth/sync/"
        : "/api/microsoft/oauth/sync/";

    try {
      setError("");
      setSyncing(provider);
      await axios.post(endpoint);
      await loadSyncStatus();
      await loadConversations();
    } catch (err) {
      console.error("Sync error:", err);
      setError(`Unable to sync ${provider}.`);
      await loadSyncStatus();
    } finally {
      setSyncing("");
    }
  };

  const downloadFile = async (messageId, attachmentId, filename) => {
    try {
      const token = localStorage.getItem("access");

      const response = await fetch(
        `${API_BASE_URL}/api/inbox/attachments/${messageId}/${attachmentId}/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Download failed");
      }

      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = filename || "attachment";
      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error("Download error:", err);
      alert("Download failed ❌");
    }
  };

  return (
    <div className="flex h-screen">

      {/* LEFT PANEL */}
      <div className="w-96 border-r flex flex-col">

        <div className="p-3 border-b space-y-2">

          {/* CONNECT */}
          <button onClick={() => window.location.href=`${API_BASE_URL}/api/google/oauth/start/`}>
            Connect Gmail
          </button>

          <button onClick={() => window.location.href=`${API_BASE_URL}/api/microsoft/oauth/start/`}>
            Connect Outlook
          </button>

          <button onClick={() => syncProvider("gmail")} disabled={syncing === "gmail"}>
            {syncing === "gmail" ? "Syncing Gmail..." : "Sync Gmail"}
          </button>

          <button onClick={() => syncProvider("outlook")} disabled={syncing === "outlook"}>
            {syncing === "outlook" ? "Syncing Outlook..." : "Sync Outlook"}
          </button>

          <div className="rounded border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
            <div className="font-semibold text-slate-900">Connected Accounts</div>

            {accounts.length === 0 ? (
              <div className="mt-1 text-slate-500">No accounts connected.</div>
            ) : (
              <div className="mt-1 space-y-1">
                {accounts.map((acc) => (
                  <div key={acc.id}>
                    <div>{acc.email_address}</div>
                    <div className="text-slate-500">
                      {acc.account_type?.toUpperCase()} - {formatSyncStatus(acc.account_type)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* COMPOSE */}
          <button onClick={() => setShowCompose(true)}>
            + Compose
          </button>

          {/* TABS */}
          <div className="flex gap-2">
            <button onClick={() => setActiveTab("inbox")}>Inbox</button>
            <button onClick={() => setActiveTab("sent")}>Sent</button>
            <button onClick={() => setActiveTab("draft")}>Draft</button>
          </div>

          {/* ACCOUNT SWITCH 🔥 */}
          <select
            value={selectedAccountId}
            onChange={(e) => setSelectedAccountId(e.target.value)}
          >
            <option value="">Select Account</option>
            {accounts.map(acc => (
              <option key={acc.id} value={acc.id}>
                {acc.email_address}
              </option>
            ))}
          </select>

          {/* SEARCH */}
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search"
          />
        </div>

        {/* LIST */}
        <div className="overflow-y-auto">
          {error && (
            <div className="p-3 text-sm text-red-600">{error}</div>
          )}

          {loading ? (
            <div className="p-3">Loading...</div>
          ) : conversations.length === 0 ? (
            <div className="p-3 text-sm text-slate-500">No conversations found.</div>
          ) : (
            conversations.map(conv => (
              <div
                key={conv.conversation_id}
                onClick={() => {
                  console.log("Clicked:", conv.conversation_id);
                  setSelectedId(conv.conversation_id);
                }}
                style={{
                  padding: 10,
                  borderBottom: "1px solid #ddd",
                  cursor: "pointer",
                  background: conv.unread_count > 0 ? "#eef6ff" : "white"
                }}
              >
                <div style={{ fontWeight: "bold", fontSize: 14 }}>
                  {conv.subject || "No Subject"}
                </div>
                <div style={{ fontSize: 11, color: "#999" }}>
                  {conv.platform?.toUpperCase()}
                </div>
                <div style={{ fontSize: 12, color: "#666" }}>
                  {conv.preview}
                </div>
              </div>
            ))
          )}
        </div>

      </div>

      {/* RIGHT PANEL */}
      <div className="flex-1 p-4">

      {!selectedId && <div>Select a conversation</div>}

      {selectedId && messages.length === 0 && <div>No messages found</div>}

      {messages.map(msg => (
        <div key={msg.id} style={{ marginBottom: 15 }}>

        <div style={{ fontWeight: "bold" }}>
          {msg.sender || "Unknown"}
        </div>

        <div style={{ fontSize: 12, color: "#888" }}>
          {msg.subject || "No Subject"}
        </div>

        <div style={{ marginTop: 5 }}>
          {msg.body || "(No content)"}
        </div>

      </div>
    ))}

    {/* 🔥 ATTACHMENTS */}
    {attachments.length > 0 && (
      <div style={{ marginTop: 20 }}>
        <b>Attachments:</b>

        {attachments.map((att, i) => (
          <div key={i}>
            📎 {att.filename}
            <button onClick={() => downloadFile(att.message_id, att.attachment_id, att.filename)}>
              Download
            </button>
          </div>
        ))}
      </div>
    )}

  </div>

  {/* TIMELINE */}

  {selectedId && (
    <ConversationTimeline
      conversationId={selectedId}
    />
  )}

      {/* COMPOSE MODAL */}
      {showCompose && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.4)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center"
        }}>
          <div style={{ background: "white", padding: 20, width: 400, position: "relative" }}>

            <button
              onClick={() => setShowCompose(false)}
              style={{ position: "absolute", top: 5, right: 5 }}
            >
              X
            </button>

            <input
              placeholder="To"
              value={composeData.to}
              onChange={(e) => setComposeData({ ...composeData, to: e.target.value })}
            />

            <input
              placeholder="Subject"
              value={composeData.subject}
              onChange={(e) => setComposeData({ ...composeData, subject: e.target.value })}
            />

            <textarea
              rows={6}
              value={composeData.body}
              onChange={(e) => setComposeData({ ...composeData, body: e.target.value })}
            />

            <div style={{ marginTop: 10 }}>
              <button onClick={saveDraft}>Save Draft</button>
              <button onClick={sendEmail}>Send</button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
