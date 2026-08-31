import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { useLocation } from "react-router-dom";

import axios from "../axiosConfig";
import ConversationTimeline from "../components/ConversationTimeline";

import {
  API_BASE_URL,
  WS_BASE_URL,
} from "../runtimeConfig";

import {
  createInboxWebSocket,
} from "../websocketAuth";


export default function Inbox() {

  // ==========================================================
  // CORE STATE
  // ==========================================================

  const [attachments, setAttachments] = useState([]);

  const [activeTab, setActiveTab] = useState("inbox");

  const [conversations, setConversations] = useState([]);

  const [selectedId, setSelectedId] = useState(null);

  const [
    selectedConversationIds,
    setSelectedConversationIds,
  ] = useState([]);

  const [messages, setMessages] = useState([]);

  const [search, setSearch] = useState("");


  // ==========================================================
  // ACCOUNT STATE
  // ==========================================================

  const [accounts, setAccounts] = useState([]);

  const [syncStatuses, setSyncStatuses] = useState([]);

  const [
    selectedAccountId,
    setSelectedAccountId,
  ] = useState("");


  // ==========================================================
  // COMPOSE STATE
  // ==========================================================

  const [showCompose, setShowCompose] = useState(false);

  const [
    composeAccountId,
    setComposeAccountId,
  ] = useState("");

  const [composeData, setComposeData] = useState({
    to: "",
    subject: "",
    body: "",
  });


  // ==========================================================
  // REPLY STATE
  // ==========================================================

  const [showReply, setShowReply] = useState(false);

  const [replyBody, setReplyBody] = useState("");

  const [replying, setReplying] = useState(false);


  // ==========================================================
  // DRAFT STATE
  // ==========================================================

  const [drafts, setDrafts] = useState([]);

  const [activeDraftId, setActiveDraftId] =
    useState(null);


  // ==========================================================
  // UI STATE
  // ==========================================================

  const [loading, setLoading] = useState(false);

  const [syncing, setSyncing] = useState("");

  const [error, setError] = useState("");

  const location = useLocation();


  // ==========================================================
  // LOAD ACCOUNTS
  // ==========================================================

  const loadAccounts = useCallback(async () => {

    try {

      const response = await axios.get(
        "/api/email-accounts/"
      );

      const data = response.data || [];

      setAccounts(data);

      if (data.length > 0) {

        setSelectedAccountId((currentId) => {

          if (currentId) {
            return currentId;
          }

          return String(data[0].id);

        });

      }

    } catch (err) {

      console.error(
        "Load accounts error:",
        err
      );

    }

  }, []);


  // ==========================================================
  // LOAD SYNC STATUS
  // ==========================================================

  const loadSyncStatus = useCallback(async () => {

    try {

      const response = await axios.get(
        "/api/inbox/sync-status/"
      );

      setSyncStatuses(
        response.data || []
      );

    } catch (err) {

      console.error(
        "Sync status error:",
        err
      );

    }

  }, []);


  // ==========================================================
  // LOAD DRAFTS
  // ==========================================================

  const loadDrafts = useCallback(async () => {

    try {

      const response = await axios.get(
        "/api/inbox/draft/list/"
      );

      setDrafts(
        response.data || []
      );

    } catch (err) {

      console.error(
        "Draft load error:",
        err
      );

      setError(
        "Unable to load drafts."
      );

    }

  }, []);


  // ==========================================================
  // INITIAL DATA
  // ==========================================================

  useEffect(() => {

    loadAccounts();
    loadSyncStatus();

  }, [
    loadAccounts,
    loadSyncStatus,
  ]);


  useEffect(() => {

    if (activeTab === "draft") {
      loadDrafts();
    }

  }, [
    activeTab,
    loadDrafts,
  ]);


  // ==========================================================
  // SYNC STATUS HELPERS
  // ==========================================================

  const getSyncStatus = (platform) => {

    return syncStatuses.find(
      (item) =>
        item.platform === platform
    );

  };


  const formatSyncStatus = (platform) => {

    const item = getSyncStatus(platform);

    if (!item) {
      return "Not synced";
    }

    const progress =
      item.status === "syncing"
        ? ` (${item.progress || 0}%)`
        : "";

    const lastSynced =
      item.last_synced_at
        ? ` | Last: ${new Date(
            item.last_synced_at
          ).toLocaleString()}`
        : "";

    return `${item.status}${progress}${lastSynced}`;

  };


  // ==========================================================
  // LOAD CONVERSATIONS
  // ==========================================================

  const loadConversations =
    useCallback(async () => {

      if (activeTab === "draft") {

        setConversations([]);
        setLoading(false);

        return;

      }

      try {

        setError("");
        setLoading(true);

        const queryParams =
          new URLSearchParams({
            folder: activeTab,
          });


        if (search.trim()) {

          queryParams.set(
            "search",
            search.trim()
          );

        }


        if (selectedAccountId) {

          queryParams.set(
            "account_id",
            selectedAccountId
          );

        }


        const response = await axios.get(
          `/api/inbox/unified-conversations/?${queryParams.toString()}`
        );


        const data =
          response.data?.results || [];


        setConversations(data);


        const urlParams =
          new URLSearchParams(
            location.search
          );


        const conversationFromUrl =
          urlParams.get(
            "conversation"
          );


        if (data.length === 0) {

          setSelectedId(null);
          setMessages([]);
          setAttachments([]);

          return;

        }


        if (conversationFromUrl) {

          const match = data.find(
            (conversation) =>
              String(
                conversation.conversation_id
              ) ===
              String(
                conversationFromUrl
              )
          );


          if (match) {

            setSelectedId(
              match.conversation_id
            );

            return;

          }

        }


        setSelectedId((currentId) => {

          const stillExists =
            data.some(
              (conversation) =>
                conversation.conversation_id ===
                currentId
            );

          if (stillExists) {
            return currentId;
          }

          return data[0].conversation_id;

        });

      } catch (err) {

        console.error(
          "Load conversations error:",
          err
        );

        setError(
          "Unable to load conversations."
        );

      } finally {

        setLoading(false);

      }

    }, [
      activeTab,
      location.search,
      search,
      selectedAccountId,
    ]);


  // ==========================================================
  // CONVERSATION SELECTION
  // ==========================================================

  const toggleConversationSelection =
    (conversationId) => {

      setSelectedConversationIds(
        (current) => {

          if (
            current.includes(
              conversationId
            )
          ) {

            return current.filter(
              (id) =>
                id !== conversationId
            );

          }

          return [
            ...current,
            conversationId,
          ];

        }
      );

    };


  const toggleSelectAll = () => {

    if (
      selectedConversationIds.length ===
        conversations.length &&
      conversations.length > 0
    ) {

      setSelectedConversationIds([]);

      return;

    }

    setSelectedConversationIds(
      conversations.map(
        (conversation) =>
          conversation.conversation_id
      )
    );

  };


  // ==========================================================
  // RELOAD WHEN FILTER CHANGES
  // ==========================================================

  useEffect(() => {

    setSelectedConversationIds([]);

    if (activeTab === "draft") {

      setSelectedId(null);
      setMessages([]);
      setAttachments([]);

      return;

    }

    loadConversations();

  }, [
    activeTab,
    loadConversations,
  ]);


  // ==========================================================
  // REALTIME REF
  // ==========================================================

  const loadConversationsRef =
    useRef(loadConversations);


  useEffect(() => {

    loadConversationsRef.current =
      loadConversations;

  }, [loadConversations]);


  // ==========================================================
  // REALTIME WEBSOCKET
  // ==========================================================

  useEffect(() => {

    const token =
      localStorage.getItem(
        "access"
      );


    if (!token) {
      return undefined;
    }


    const socket =
      createInboxWebSocket({
        baseUrl:
          WS_BASE_URL,
        accessToken:
          token,
      });


    socket.onopen = () => {

      console.log(
        "WS Connected"
      );

    };


    socket.onmessage = (event) => {

      console.log(
        "Realtime update:",
        event.data
      );

      loadConversationsRef.current();

    };


    socket.onerror = (err) => {

      console.error(
        "WS Error:",
        err
      );

    };


    socket.onclose = () => {

      console.log(
        "WS Closed"
      );

    };


    return () => {

      socket.close();

    };

  }, []);


  // ==========================================================
  // LOAD CONVERSATION THREAD
  // ==========================================================

  useEffect(() => {

    if (!selectedId) {
      return;
    }


    if (activeTab === "draft") {
      return;
    }


    axios
      .get(
        `/api/inbox/conversations/${selectedId}/`
      )
      .then((response) => {

        setMessages(
          response.data?.messages || []
        );

        setAttachments(
          response.data?.attachments || []
        );


        return axios.post(
          `/api/inbox/conversation/${selectedId}/mark-read/`
        );

      })
      .then(() => {

        setConversations(
          (items) =>
            items.map(
              (item) =>
                item.conversation_id ===
                selectedId
                  ? {
                      ...item,
                      unread_count: 0,
                    }
                  : item
            )
        );

      })
      .catch((err) => {

        console.error(
          "Thread load error:",
          err
        );

      });

  }, [
    selectedId,
    activeTab,
  ]);


  // ==========================================================
  // SEND EMAIL
  // ==========================================================

  const sendEmail = async () => {

    try {

      setError("");


      await axios.post(
        "/api/inbox/send/",
        {
          to: composeData.to,
          subject:
            composeData.subject,
          body:
            composeData.body,
          account_id:
            composeAccountId,
        }
      );


      setShowCompose(false);

      setActiveDraftId(null);

      setComposeData({
        to: "",
        subject: "",
        body: "",
      });

      setSelectedId(null);

      setActiveTab("sent");

    } catch (err) {

      console.error(
        "Send email error:",
        err
      );

      setError(
        err.response?.data?.error ||
          "Unable to send email."
      );

    }

  };


  // ==========================================================
  // SEND REPLY
  // ==========================================================

  const sendReply = async () => {

    if (!selectedId) {

      setError(
        "Select a conversation before replying."
      );

      return;

    }


    if (!replyBody.trim()) {

      setError(
        "Reply message cannot be empty."
      );

      return;

    }


    try {

      setError("");

      setReplying(true);


      await axios.post(
        `/api/inbox/conversations/${selectedId}/reply/`,
        {
          body:
            replyBody.trim(),

        }
      );


      setReplyBody("");

      setShowReply(false);


      const response =
        await axios.get(
          `/api/inbox/conversations/${selectedId}/`
        );


      setMessages(
        response.data?.messages || []
      );


      setAttachments(
        response.data?.attachments || []
      );


      await loadConversations();

    } catch (err) {

      console.error(
        "Reply error:",
        err
      );


      setError(
        err.response?.data?.error ||
          "Unable to send reply."
      );

    } finally {

      setReplying(false);

    }

  };


  // ==========================================================
  // SAVE DRAFT
  // ==========================================================

  const saveDraft = async () => {

    try {

      setError("");


      await axios.post(
        "/api/inbox/draft/save/",
        {
          conversation_id:
            selectedId,

          subject:
            composeData.subject,

          body:
            composeData.body,

          recipients:
            composeData.to,

          account_id:
            composeAccountId,
        }
      );


      setShowCompose(false);

      setActiveDraftId(null);

      setSelectedId(null);


      setComposeData({
        to: "",
        subject: "",
        body: "",
      });


      setActiveTab("draft");

      await loadDrafts();

    } catch (err) {

      console.error(
        "Save draft error:",
        err
      );


      setError(
        err.response?.data?.error ||
          "Unable to save draft."
      );

    }

  };


  // ==========================================================
  // SEND DRAFT
  // ==========================================================

  const sendDraft = async () => {

    if (!activeDraftId) {

      setError(
        "No draft selected."
      );

      return;

    }


    try {

      setError("");


      await axios.post(
        `/api/inbox/draft/send/${activeDraftId}/`
      );


      setShowCompose(false);

      setActiveDraftId(null);

      setSelectedId(null);


      setComposeData({
        to: "",
        subject: "",
        body: "",
      });


      await loadDrafts();

      setActiveTab("sent");

    } catch (err) {

      console.error(
        "Draft send error:",
        err
      );


      setError(
        err.response?.data?.error ||
          "Unable to send draft."
      );

    }

  };


  // ==========================================================
  // CONNECT PROVIDER
  // ==========================================================

  const connectProvider =
    async (provider) => {

      const endpoint =
        provider === "gmail"
          ? "/api/google/oauth/start/"
          : "/api/microsoft/oauth/start/";


      try {

        setError("");


        const response =
          await axios.get(
            endpoint
          );


        const authorizationUrl =
          response.data
            ?.authorization_url;


        if (!authorizationUrl) {

          throw new Error(
            "OAuth authorization URL was not returned."
          );

        }


        window.location.assign(
          authorizationUrl
        );

      } catch (err) {

        console.error(
          `${provider} connect error:`,
          err
        );


        setError(
          `Unable to connect ${provider}.`
        );

      }

    };


  // ==========================================================
  // SYNC PROVIDER
  // ==========================================================

  const syncProvider =
    async (provider) => {

      const endpoint =
        provider === "gmail"
          ? "/api/google/oauth/sync/"
          : "/api/microsoft/oauth/sync/";


      try {

        setError("");

        setSyncing(provider);


        await axios.post(
          endpoint
        );


        await loadSyncStatus();

        await loadConversations();

      } catch (err) {

        console.error(
          "Sync error:",
          err
        );


        setError(
          `Unable to sync ${provider}.`
        );


        await loadSyncStatus();

      } finally {

        setSyncing("");

      }

    };


  // ==========================================================
  // BULK MARK READ
  // ==========================================================

  const bulkMarkRead = async () => {

    if (
      selectedConversationIds.length === 0
    ) {
      return;
    }


    try {

      setError("");


      const response =
        await axios.post(
          "/api/inbox/conversation/bulk-mark-read/",
          {
            conversation_ids:
              selectedConversationIds,
          }
        );


      const errors =
        response.data?.errors || [];


      if (errors.length > 0) {

        console.error(
          "Bulk mark-read partial errors:",
          errors
        );


        setError(
          `${errors.length} conversation(s) could not be marked as read.`
        );

      }


      setSelectedConversationIds([]);

      await loadConversations();

    } catch (err) {

      console.error(
        "Bulk mark-read error:",
        err
      );


      setError(
        err.response?.data?.error ||
          "Unable to mark selected conversations as read."
      );

    }

  };


  // ==========================================================
  // BULK STAR
  // ==========================================================

  const bulkToggleStar =
    async () => {

      if (
        selectedConversationIds.length ===
        0
      ) {
        return;
      }


      try {

        setError("");


        const response =
          await axios.post(
            "/api/inbox/conversation/bulk-toggle-star/",
            {
              conversation_ids:
                selectedConversationIds,
            }
          );


        const errors =
          response.data?.errors || [];


        if (errors.length > 0) {

          console.error(
            "Bulk star partial errors:",
            errors
          );


          setError(
            `${errors.length} conversation(s) could not be updated.`
          );

        }


        setSelectedConversationIds([]);

        await loadConversations();

      } catch (err) {

        console.error(
          "Bulk star error:",
          err
        );


        setError(
          err.response?.data?.error ||
            "Unable to update selected conversations."
        );

      }

    };


  // ==========================================================
  // ATTACHMENT DOWNLOAD
  // ==========================================================

  const downloadFile = async (
    messageId,
    attachmentId,
    filename
  ) => {

    try {

      const token =
        localStorage.getItem(
          "access"
        );


      const response =
        await fetch(
          `${API_BASE_URL}/api/inbox/attachments/${messageId}/${attachmentId}/`,
          {
            method: "GET",

            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );


      if (!response.ok) {

        throw new Error(
          "Download failed"
        );

      }


      const blob =
        await response.blob();


      const url =
        window.URL.createObjectURL(
          blob
        );


      const anchor =
        document.createElement(
          "a"
        );


      anchor.href = url;

      anchor.download =
        filename ||
        "attachment";


      document.body.appendChild(
        anchor
      );


      anchor.click();

      anchor.remove();


      window.URL.revokeObjectURL(
        url
      );

    } catch (err) {

      console.error(
        "Download error:",
        err
      );


      setError(
        "Unable to download attachment."
      );

    }

  };


  // ==========================================================
  // OPEN DRAFT
  // ==========================================================

  const openDraft = (draft) => {

    setError("");

    setActiveDraftId(
      draft.id
    );


    setComposeData({
      to:
        draft.recipients || "",

      subject:
        draft.subject || "",

      body:
        draft.body || "",
    });


    if (
      draft.email_account_id
    ) {

      setComposeAccountId(
        String(
          draft.email_account_id
        )
      );

    }


    setSelectedId(
      draft.conversation_id ||
        null
    );


    setShowCompose(true);

  };


  // ==========================================================
  // CLOSE COMPOSE
  // ==========================================================

  const closeCompose = () => {

    setShowCompose(false);

    setActiveDraftId(null);


    if (activeTab === "draft") {
      setSelectedId(null);
    }


    setComposeData({
      to: "",
      subject: "",
      body: "",
    });

  };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="flex h-screen">


      {/* =====================================================
          LEFT PANEL
      ====================================================== */}

      <div className="w-96 border-r flex flex-col">


        {/* ===================================================
            TOP CONTROLS
        ==================================================== */}

        <div className="p-3 border-b space-y-2">


          {/* CONNECT */}

          <div className="flex gap-2">

            <button
              type="button"
              onClick={() =>
                connectProvider(
                  "gmail"
                )
              }
            >
              Connect Gmail
            </button>


            <button
              type="button"
              onClick={() =>
                connectProvider(
                  "outlook"
                )
              }
            >
              Connect Outlook
            </button>

          </div>


          {/* SYNC */}

          <div className="flex gap-2">

            <button
              type="button"
              onClick={() =>
                syncProvider(
                  "gmail"
                )
              }
              disabled={
                syncing === "gmail"
              }
            >
              {syncing === "gmail"
                ? "Syncing Gmail..."
                : "Sync Gmail"}
            </button>


            <button
              type="button"
              onClick={() =>
                syncProvider(
                  "outlook"
                )
              }
              disabled={
                syncing === "outlook"
              }
            >
              {syncing === "outlook"
                ? "Syncing Outlook..."
                : "Sync Outlook"}
            </button>

          </div>


          {/* CONNECTED ACCOUNTS */}

          <div className="rounded border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">

            <div className="font-semibold text-slate-900">
              Connected Accounts
            </div>


            {accounts.length === 0 ? (

              <div className="mt-1 text-slate-500">
                No accounts connected.
              </div>

            ) : (

              <div className="mt-1 space-y-1">

                {accounts.map(
                  (account) => (

                    <div
                      key={
                        account.id
                      }
                    >

                      <div>
                        {
                          account.email_address
                        }
                      </div>

                      <div className="text-slate-500">

                        {account.account_type
                          ?.toUpperCase()}

                        {" - "}

                        {formatSyncStatus(
                          account.account_type
                        )}

                      </div>

                    </div>

                  )
                )}

              </div>

            )}

          </div>


          {/* COMPOSE */}

          <button
            type="button"
            onClick={() => {

              setActiveDraftId(
                null
              );

              setSelectedId(
                null
              );

              setComposeData({
                to: "",
                subject: "",
                body: "",
              });

              setComposeAccountId(
                selectedAccountId ||
                (
                  accounts.length > 0
                    ? String(accounts[0].id)
                    : ""
                )
              );

              setShowCompose(
                true
              );

            }}
          >
            + Compose
          </button>


          {/* TABS */}

          <div className="flex gap-2">

            <button
              type="button"
              onClick={() => {

                setActiveTab(
                  "inbox"
                );

                setSelectedConversationIds(
                  []
                );

              }}
            >
              Inbox
            </button>


            <button
              type="button"
              onClick={() => {

                setActiveTab(
                  "sent"
                );

                setSelectedConversationIds(
                  []
                );

              }}
            >
              Sent
            </button>


            <button
              type="button"
              onClick={() => {

                setActiveTab(
                  "draft"
                );

                setSelectedId(
                  null
                );

                setSelectedConversationIds(
                  []
                );

                setMessages(
                  []
                );

                setAttachments(
                  []
                );

              }}
            >
              Draft
            </button>

          </div>


          {/* ACCOUNT SWITCH */}

          <select
            value={
              selectedAccountId
            }
            onChange={(event) =>
              setSelectedAccountId(
                event.target.value
              )
            }
          >

            <option value="">
              Select Account
            </option>


            {accounts.map(
              (account) => (

                <option
                  key={
                    account.id
                  }
                  value={
                    account.id
                  }
                >
                  {
                    account.email_address
                  }
                </option>

              )
            )}

          </select>


          {/* SEARCH */}

          {activeTab !== "draft" && (

            <input
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
              placeholder="Search"
            />

          )}

        </div>


        {/* ===================================================
            SELECT ALL
        ==================================================== */}

        {activeTab !== "draft" &&
          conversations.length > 0 && (

            <div className="border-b p-2">

              <button
                type="button"
                onClick={
                  toggleSelectAll
                }
                className="rounded border px-2 py-1 text-xs"
              >

                {selectedConversationIds.length ===
                conversations.length
                  ? "Clear All"
                  : "Select All"}

              </button>

            </div>

          )}


        {/* ===================================================
            BULK TOOLBAR
        ==================================================== */}

        {activeTab !== "draft" &&
          selectedConversationIds.length >
            0 && (

            <div className="border-b p-2 flex gap-2 items-center flex-wrap">

              <span className="text-xs text-slate-600">

                {
                  selectedConversationIds.length
                }{" "}
                selected

              </span>


              <button
                type="button"
                onClick={
                  bulkMarkRead
                }
                className="rounded border px-2 py-1 text-xs"
              >
                Mark Read
              </button>


              <button
                type="button"
                onClick={
                  bulkToggleStar
                }
                className="rounded border px-2 py-1 text-xs"
              >
                Toggle Star
              </button>


              <button
                type="button"
                onClick={() =>
                  setSelectedConversationIds(
                    []
                  )
                }
                className="rounded border px-2 py-1 text-xs"
              >
                Clear
              </button>

            </div>

          )}


        {/* ===================================================
            LIST
        ==================================================== */}

        <div className="overflow-y-auto flex-1">


          {error && (

            <div className="p-3 text-sm text-red-600">
              {error}
            </div>

          )}


          {/* DRAFT LIST */}

          {activeTab === "draft" ? (

            drafts.length === 0 ? (

              <div className="p-3 text-sm text-slate-500">
                No drafts found.
              </div>

            ) : (

              drafts.map(
                (draft) => (

                  <div
                    key={
                      draft.id
                    }
                    onClick={() =>
                      openDraft(
                        draft
                      )
                    }
                    style={{
                      padding: 10,
                      borderBottom:
                        "1px solid #ddd",
                      cursor:
                        "pointer",
                    }}
                  >

                    <div
                      style={{
                        fontWeight:
                          "bold",
                        fontSize: 14,
                      }}
                    >
                      {draft.subject ||
                        "No Subject"}
                    </div>


                    <div
                      style={{
                        fontSize: 12,
                        color: "#666",
                      }}
                    >
                      {draft.recipients ||
                        "No recipient"}
                    </div>


                    <div
                      style={{
                        fontSize: 11,
                        color: "#999",
                        marginTop: 3,
                      }}
                    >
                      Draft
                    </div>

                  </div>

                )
              )

            )

          ) : loading ? (

            <div className="p-3">
              Loading...
            </div>

          ) : conversations.length ===
            0 ? (

            <div className="p-3 text-sm text-slate-500">
              No conversations found.
            </div>

          ) : (

            conversations.map(
              (conversation) => (

                <div
                  key={
                    conversation.conversation_id
                  }
                  onClick={() => {

                    setSelectedId(
                      conversation.conversation_id
                    );

                  }}
                  style={{
                    padding: 10,
                    borderBottom:
                      "1px solid #ddd",
                    cursor:
                      "pointer",

                    background:
                      conversation.unread_count >
                      0
                        ? "#eef6ff"
                        : "white",
                  }}
                >

                  <div
                    style={{
                      display:
                        "flex",
                      alignItems:
                        "flex-start",
                      gap: 8,
                    }}
                  >

                    {/* CHECKBOX */}

                    <input
                      type="checkbox"
                      checked={selectedConversationIds.includes(
                        conversation.conversation_id
                      )}
                      onChange={() =>
                        toggleConversationSelection(
                          conversation.conversation_id
                        )
                      }
                      onClick={(
                        event
                      ) => {

                        event.stopPropagation();

                      }}
                    />


                    {/* CONTENT */}

                    <div
                      style={{
                        flex: 1,
                        minWidth: 0,
                      }}
                    >

                      <div
                        style={{
                          fontWeight:
                            "bold",
                          fontSize:
                            14,
                        }}
                      >

                        {conversation.is_starred
                          ? "★ "
                          : ""}

                        {conversation.subject ||
                          "No Subject"}

                      </div>


                      {activeTab === "sent" && (
                        <div
                          style={{
                            fontSize: 12,
                            color: "#666",
                            marginTop: 2,
                          }}
                        >
                          To: {
                            conversation.recipients ||
                            "Unknown recipient"
                          }
                        </div>
                      )}

                      <div
                        style={{
                          fontSize:
                            11,
                          color:
                            "#999",
                        }}
                      >
                        {conversation.platform
                          ?.toUpperCase()}
                      </div>


                      <div
                        style={{
                          fontSize:
                            12,
                          color:
                            "#666",
                        }}
                      >
                        {
                          conversation.preview
                        }
                      </div>

                    </div>

                  </div>

                </div>

              )
            )

          )}

        </div>

      </div>


      {/* =====================================================
          RIGHT AREA
      ====================================================== */}

      <div className="flex-1 flex min-w-0">


        {/* ===================================================
            MESSAGE DETAIL
        ==================================================== */}

        <div className="flex-1 p-4 overflow-y-auto">


          {!selectedId &&
            activeTab !== "draft" && (

              <div>
                Select a conversation
              </div>

            )}


          {selectedId &&
            activeTab !== "draft" &&
            messages.length === 0 && (

              <div>
                No messages found
              </div>

            )}


          {/* REPLY ACTION */}

          {selectedId &&
            activeTab !== "draft" &&
            messages.length > 0 && (

              <div className="mb-4 flex gap-2">

                <button
                  type="button"
                  onClick={() => {

                    setError("");

                    setShowReply(
                      true
                    );

                  }}
                  className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white"
                >
                  Reply
                </button>

              </div>

            )}


          {/* MESSAGES */}

          {activeTab !== "draft" &&
            messages.map(
              (message) => (

                <div
                  key={
                    message.id
                  }
                  style={{
                    marginBottom:
                      15,
                  }}
                >

                  <div
                    style={{
                      fontWeight:
                        "bold",
                    }}
                  >
                    {activeTab === "sent"
                      ? (
                          "To: " +
                          (
                            message.recipients ||
                            "Unknown recipient"
                          )
                        )
                      : (
                          message.sender ||
                          "Unknown"
                        )}
                  </div>


                  <div
                    style={{
                      fontSize:
                        12,
                      color:
                        "#888",
                    }}
                  >
                    {message.subject ||
                      "No Subject"}
                  </div>


                  <div
                    style={{
                      marginTop:
                        5,
                    }}
                  >
                    {message.body ||
                      "(No content)"}
                  </div>

                </div>

              )
            )}


          {/* ATTACHMENTS */}

          {activeTab !== "draft" &&
            attachments.length > 0 && (

              <div
                style={{
                  marginTop: 20,
                }}
              >

                <b>
                  Attachments:
                </b>


                {attachments.map(
                  (
                    attachment,
                    index
                  ) => (

                    <div
                      key={
                        attachment.attachment_id ||
                        index
                      }
                    >

                      📎{" "}
                      {
                        attachment.filename
                      }


                      <button
                        type="button"
                        onClick={() =>
                          downloadFile(
                            attachment.message_id,
                            attachment.attachment_id,
                            attachment.filename
                          )
                        }
                      >
                        Download
                      </button>

                    </div>

                  )
                )}

              </div>

            )}

        </div>


        {/* ===================================================
            TIMELINE
        ==================================================== */}

        {selectedId &&
          activeTab !== "draft" && (

            <ConversationTimeline
              conversationId={
                selectedId
              }
            />

          )}

      </div>


      {/* =====================================================
          COMPOSE MODAL
      ====================================================== */}

      {showCompose && (

        <div
          style={{
            position:
              "fixed",
            inset: 0,
            background:
              "rgba(0,0,0,0.4)",
            display:
              "flex",
            justifyContent:
              "center",
            alignItems:
              "center",
            zIndex: 50,
          }}
        >

          <div
            style={{
              background:
                "white",
              padding: 20,
              width: 420,
              maxWidth:
                "90vw",
              position:
                "relative",
            }}
          >

            {/* CLOSE */}

            <button
              type="button"
              onClick={
                closeCompose
              }
              style={{
                position:
                  "absolute",
                top: 5,
                right: 5,
              }}
            >
              X
            </button>


            <div
              style={{
                fontWeight:
                  600,
                marginBottom:
                  12,
              }}
            >

              {activeDraftId
                ? "Edit Draft"
                : "Compose"}

            </div>


            {/* FROM */}

            <select
              value={composeAccountId}
              onChange={(event) =>
                setComposeAccountId(
                  event.target.value
                )
              }
              style={{
                width: "100%",
                marginBottom: 8,
              }}
            >
              <option value="">
                Select sending account
              </option>

              {accounts.map(
                (account) => (
                  <option
                    key={account.id}
                    value={account.id}
                  >
                    {account.email_address}
                    {" ("}
                    {account.account_type?.toUpperCase()}
                    {")"}
                  </option>
                )
              )}
            </select>


            {/* TO */}

            <input
              placeholder="To"
              value={
                composeData.to
              }
              onChange={(event) =>
                setComposeData({
                  ...composeData,
                  to:
                    event.target.value,
                })
              }
              style={{
                width:
                  "100%",
                marginBottom:
                  8,
              }}
            />


            {/* SUBJECT */}

            <input
              placeholder="Subject"
              value={
                composeData.subject
              }
              onChange={(event) =>
                setComposeData({
                  ...composeData,
                  subject:
                    event.target.value,
                })
              }
              style={{
                width:
                  "100%",
                marginBottom:
                  8,
              }}
            />


            {/* BODY */}

            <textarea
              rows={8}
              value={
                composeData.body
              }
              onChange={(event) =>
                setComposeData({
                  ...composeData,
                  body:
                    event.target.value,
                })
              }
              style={{
                width:
                  "100%",
              }}
            />


            {/* ACTIONS */}

            <div
              style={{
                marginTop:
                  10,
                display:
                  "flex",
                gap: 8,
              }}
            >

              <button
                type="button"
                onClick={
                  saveDraft
                }
              >
                Save Draft
              </button>


              {activeDraftId ? (

                <button
                  type="button"
                  onClick={
                    sendDraft
                  }
                >
                  Send Draft
                </button>

              ) : (

                <button
                  type="button"
                  onClick={
                    sendEmail
                  }
                >
                  Send
                </button>

              )}

            </div>

          </div>

        </div>

      )}


      {/* =====================================================
          REPLY MODAL
      ====================================================== */}

      {showReply &&
        selectedId && (

          <div
            style={{
              position:
                "fixed",
              inset: 0,
              background:
                "rgba(0,0,0,0.4)",
              display:
                "flex",
              justifyContent:
                "center",
              alignItems:
                "center",
              zIndex:
                60,
            }}
          >

            <div
              style={{
                background:
                  "white",
                padding:
                  20,
                width:
                  500,
                maxWidth:
                  "90vw",
                position:
                  "relative",
              }}
            >

              {/* CLOSE */}

              <button
                type="button"
                onClick={() => {

                  if (
                    !replying
                  ) {

                    setShowReply(
                      false
                    );

                    setReplyBody(
                      ""
                    );

                  }

                }}
                disabled={
                  replying
                }
                style={{
                  position:
                    "absolute",
                  top: 8,
                  right: 8,
                }}
              >
                X
              </button>


              <div
                style={{
                  fontWeight:
                    600,
                  marginBottom:
                    12,
                }}
              >
                Reply
              </div>


              <textarea
                rows={8}
                value={
                  replyBody
                }
                onChange={(
                  event
                ) =>
                  setReplyBody(
                    event.target.value
                  )
                }
                placeholder="Write your reply..."
                disabled={
                  replying
                }
                style={{
                  width:
                    "100%",
                  padding:
                    10,
                  border:
                    "1px solid #ddd",
                  borderRadius:
                    6,
                }}
              />


              <div
                style={{
                  marginTop:
                    12,
                  display:
                    "flex",
                  justifyContent:
                    "flex-end",
                  gap: 8,
                }}
              >

                <button
                  type="button"
                  disabled={
                    replying
                  }
                  onClick={() => {

                    setShowReply(
                      false
                    );

                    setReplyBody(
                      ""
                    );

                  }}
                >
                  Cancel
                </button>


                <button
                  type="button"
                  onClick={
                    sendReply
                  }
                  disabled={
                    replying ||
                    !replyBody.trim()
                  }
                >

                  {replying
                    ? "Sending..."
                    : "Send Reply"}

                </button>

              </div>

            </div>

          </div>

        )}

    </div>

  );

}