import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { useLocation } from "react-router-dom";

import axios from "../axiosConfig";
import ConversationTimeline from "../components/ConversationTimeline";

import RecipientChipInput, {
  parseRecipientString,
  serializeRecipients,
} from "../components/RecipientChipInput";

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
    to: [],
    cc: [],
    bcc: [],
    subject: "",
    body: "",
  });

  const [
    forwardSourceId,
    setForwardSourceId,
  ] = useState(null);


  // ==========================================================
  // REPLY STATE
  // ==========================================================

  const [showReply, setShowReply] = useState(false);

  const [replyBody, setReplyBody] = useState("");

  const [replyMode, setReplyMode] = useState("reply");

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

    if (
      composeData.to.length === 0
    ) {

      setError(
        "Add at least one recipient."
      );

      return;

    }


    try {

      setError("");


      const sendEndpoint =
        forwardSourceId
          ? `/api/inbox/message/${forwardSourceId}/forward/`
          : "/api/inbox/send/";


      await axios.post(
        sendEndpoint,
        {
          to:
            composeData.to,

          cc:
            composeData.cc,

          bcc:
            composeData.bcc,

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

      setForwardSourceId(null);

      setComposeData({
        to: [],
    cc: [],
    bcc: [],
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

          mode:
            replyMode,

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
            serializeRecipients(
              composeData.to
            ),

          to:
            composeData.to,

          cc:
            composeData.cc,

          bcc:
            composeData.bcc,

          account_id:
            composeAccountId,
        }
      );


      setShowCompose(false);

      setActiveDraftId(null);

      setSelectedId(null);


      setComposeData({
        to: [],
    cc: [],
    bcc: [],
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
        to: [],
    cc: [],
    bcc: [],
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
  // CONVERSATION MAIL OPERATIONS
  // ==========================================================

  const markConversationUnread =
    async () => {

      if (!selectedId) {
        return;
      }


      try {

        setError("");


        await axios.post(
          `/api/inbox/conversation/${selectedId}/mark-read/`,
          {
            is_read:
              false,
          }
        );


        await loadConversations();

      } catch (err) {

        console.error(
          "Mark unread error:",
          err
        );


        setError(
          err.response?.data?.error ||
            "Unable to mark conversation unread."
        );

      }

    };


  const toggleSelectedConversationStar =
    async () => {

      if (!selectedId) {
        return;
      }


      try {

        setError("");


        await axios.post(
          `/api/inbox/conversation/${selectedId}/toggle-star/`
        );


        await loadConversations();

      } catch (err) {

        console.error(
          "Toggle star error:",
          err
        );


        setError(
          err.response?.data?.error ||
            "Unable to update conversation star."
        );

      }

    };


  const trashSelectedConversation =
    async () => {

      if (!selectedId) {
        return;
      }


      const confirmed =
        window.confirm(
          "Move this conversation to Trash?"
        );


      if (!confirmed) {
        return;
      }


      try {

        setError("");


        await axios.post(
          `/api/inbox/conversation/${selectedId}/delete/`
        );


        setSelectedId(null);

        setMessages([]);

        setAttachments([]);

        await loadConversations();

      } catch (err) {

        console.error(
          "Trash conversation error:",
          err
        );


        setError(
          err.response?.data?.error ||
            "Unable to move conversation to Trash."
        );

      }

    };


  const openSelectedMessageInProvider =
    async () => {

      const latestMessage =
        messages.length > 0
          ? messages[
              messages.length - 1
            ]
          : null;


      if (!latestMessage) {

        setError(
          "No provider message is available."
        );

        return;

      }


      try {

        setError("");


        const response =
          await axios.get(
            `/api/inbox/message/${latestMessage.id}/provider-open/`
          );


        const providerUrl =
          response.data?.url;


        if (!providerUrl) {

          throw new Error(
            "Provider URL missing"
          );

        }


        window.open(
          providerUrl,
          "_blank",
          "noopener,noreferrer"
        );

      } catch (err) {

        console.error(
          "Open provider error:",
          err
        );


        setError(
          err.response?.data?.error ||
            "Provider message is not available yet."
        );

      }

    };


  const beginForward = () => {

    const latestMessage =
      messages.length > 0
        ? messages[
            messages.length - 1
          ]
        : null;


    if (!latestMessage) {

      setError(
        "No message is available to forward."
      );

      return;

    }


    setError("");

    setActiveDraftId(null);

    setForwardSourceId(
      latestMessage.id
    );


    setComposeAccountId(
      latestMessage.email_account_id
        ? String(
            latestMessage.email_account_id
          )
        : ""
    );


    const currentSubject =
      latestMessage.subject ||
      "No Subject";


    const forwardSubject =
      currentSubject
        .toLowerCase()
        .startsWith(
          "fwd:"
        )
          ? currentSubject
          : `Fwd: ${currentSubject}`;


    setComposeData({
      to: [],
      cc: [],
      bcc: [],
      subject:
        forwardSubject,
      body:
        "",
    });


    setShowCompose(
      true
    );

  };


  // ==========================================================
  // OPEN DRAFT
  // ==========================================================

  const openDraft = (draft) => {

    setError("");

    setForwardSourceId(null);

    setActiveDraftId(
      draft.id
    );


    const draftRecipientMeta =
      draft.recipient_meta || {};


    const structuredDraftTo =
      Array.isArray(
        draftRecipientMeta.to
      )
      &&
      draftRecipientMeta.to.length > 0
        ? draftRecipientMeta.to
        : parseRecipientString(
            draft.recipients
          );


    setComposeData({
      to:
        structuredDraftTo,

      cc:
        Array.isArray(
          draftRecipientMeta.cc
        )
          ? draftRecipientMeta.cc
          : [],

      bcc:
        Array.isArray(
          draftRecipientMeta.bcc
        )
          ? draftRecipientMeta.bcc
          : [],

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

    setForwardSourceId(null);


    if (activeTab === "draft") {
      setSelectedId(null);
    }


    setComposeData({
      to: [],
    cc: [],
    bcc: [],
      subject: "",
      body: "",
    });

  };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="min-h-[calc(100vh-118px)] bg-slate-50/70 p-3 sm:p-4 lg:p-5">

      <div className="mx-auto flex min-h-[720px] max-w-[1680px] flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm lg:h-[calc(100vh-154px)] lg:flex-row">


        {/* ===================================================
            MAILBOX / CONVERSATION RAIL
        ==================================================== */}

        <aside className="flex min-h-0 w-full shrink-0 flex-col border-b border-slate-200 bg-white lg:w-[390px] lg:border-b-0 lg:border-r">

          {/* ===============================================
              WORKSPACE CONTROL
          ================================================ */}

          <div className="border-b border-slate-100 px-4 py-4">

            <div className="flex items-center justify-between gap-3">

              <div>

                <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-slate-400">
                  Connected communication
                </p>

                <h2 className="mt-1 text-base font-semibold tracking-tight text-slate-950">
                  Mail workspace
                </h2>

              </div>


              <button
                type="button"
                onClick={() => {

                  setActiveDraftId(
                    null
                  );

                  setForwardSourceId(
                    null
                  );

                  setSelectedId(
                    null
                  );

                  setComposeData({
                    to:
                      [],
                    cc:
                      [],
                    bcc:
                      [],
                    subject:
                      "",
                    body:
                      "",
                  });

                  setComposeAccountId(
                    selectedAccountId ||
                    (
                      accounts.length > 0
                        ? String(
                            accounts[
                              0
                            ].id
                          )
                        : ""
                    )
                  );

                  setShowCompose(
                    true
                  );

                }}
                className="rounded-xl bg-slate-950 px-3.5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-slate-800"
              >
                + Compose
              </button>

            </div>


            {/* =============================================
                PROVIDER HEALTH
            ============================================== */}

            <div className="mt-4 grid grid-cols-2 gap-2">

              {[
                {
                  provider:
                    "gmail",
                  label:
                    "Gmail",
                },
                {
                  provider:
                    "outlook",
                  label:
                    "Microsoft 365",
                },
              ].map(
                (provider) => {

                  const connected =
                    accounts.some(
                      (account) =>
                        account.account_type ===
                        provider.provider
                    );


                  const busy =
                    syncing ===
                    provider.provider;


                  return (

                    <div
                      key={
                        provider.provider
                      }
                      className="rounded-2xl border border-slate-200 bg-slate-50/70 p-3"
                    >

                      <div className="flex items-center justify-between gap-2">

                        <span className="text-xs font-semibold text-slate-800">
                          {provider.label}
                        </span>

                        <span
                          className={`h-2 w-2 rounded-full ${
                            connected
                              ? "bg-emerald-500"
                              : "bg-slate-300"
                          }`}
                        />

                      </div>


                      <p className="mt-1 line-clamp-2 min-h-[32px] text-[10px] leading-4 text-slate-500">
                        {formatSyncStatus(
                          provider.provider
                        )}
                      </p>


                      <div className="mt-2 flex gap-1.5">

                        {!connected && (

                          <button
                            type="button"
                            onClick={() =>
                              connectProvider(
                                provider.provider
                              )
                            }
                            className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50"
                          >
                            Connect
                          </button>

                        )}


                        {connected && (

                          <button
                            type="button"
                            disabled={
                              busy
                            }
                            onClick={() =>
                              syncProvider(
                                provider.provider
                              )
                            }
                            className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50 disabled:cursor-wait disabled:opacity-50"
                          >
                            {busy
                              ? "Syncing..."
                              : "Sync"}
                          </button>

                        )}

                      </div>

                    </div>

                  );

                }
              )}

            </div>


            {/* =============================================
                ACCOUNT FILTER
            ============================================== */}

            <div className="mt-3">

              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                Mailbox
              </label>

              <select
                value={
                  selectedAccountId
                }
                onChange={(event) =>
                  setSelectedAccountId(
                    event.target.value
                  )
                }
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-medium text-slate-700 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
              >

                <option value="">
                  All connected mailboxes
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
                      {account.email_address}
                      {" ? "}
                      {account.account_type
                        ?.toUpperCase()}
                    </option>

                  )
                )}

              </select>

            </div>

          </div>


          {/* ===============================================
              FOLDER NAVIGATION
          ================================================ */}

          <div className="border-b border-slate-100 px-4 py-3">

            <div className="grid grid-cols-3 rounded-xl bg-slate-100 p-1">

              {[
                [
                  "inbox",
                  "Inbox",
                ],
                [
                  "sent",
                  "Sent",
                ],
                [
                  "draft",
                  "Drafts",
                ],
              ].map(
                (
                  [
                    value,
                    label,
                  ]
                ) => (

                  <button
                    type="button"
                    key={
                      value
                    }
                    onClick={() => {

                      setActiveTab(
                        value
                      );

                      setSelectedConversationIds(
                        []
                      );


                      if (
                        value ===
                        "draft"
                      ) {

                        setSelectedId(
                          null
                        );

                        setMessages(
                          []
                        );

                        setAttachments(
                          []
                        );

                      }

                    }}
                    className={`rounded-lg px-2 py-2 text-xs font-semibold transition ${
                      activeTab ===
                      value
                        ? "bg-white text-slate-950 shadow-sm"
                        : "text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    {label}
                  </button>

                )
              )}

            </div>


            {activeTab !==
              "draft" && (

              <div className="mt-3">

                <input
                  value={
                    search
                  }
                  onChange={(event) =>
                    setSearch(
                      event.target.value
                    )
                  }
                  placeholder="Search this mailbox..."
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-slate-300 focus:bg-white focus:ring-2 focus:ring-slate-100"
                />

              </div>

            )}

          </div>


          {/* ===============================================
              BULK CONTROL
          ================================================ */}

          {activeTab !==
            "draft" &&
            conversations.length >
              0 && (

              <div className="border-b border-slate-100 px-4 py-2.5">

                <div className="flex flex-wrap items-center gap-2">

                  <button
                    type="button"
                    onClick={
                      toggleSelectAll
                    }
                    className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50"
                  >
                    {selectedConversationIds.length ===
                    conversations.length
                      ? "Clear selection"
                      : "Select all"}
                  </button>


                  {selectedConversationIds.length >
                    0 && (

                    <>
                      <span className="text-[10px] font-semibold text-slate-400">
                        {selectedConversationIds.length} selected
                      </span>

                      <button
                        type="button"
                        onClick={
                          bulkMarkRead
                        }
                        className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-200"
                      >
                        Mark read
                      </button>

                      <button
                        type="button"
                        onClick={
                          bulkToggleStar
                        }
                        className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-200"
                      >
                        Toggle star
                      </button>

                    </>

                  )}

                </div>

              </div>

            )}


          {/* ===============================================
              CONVERSATION LIST
          ================================================ */}

          <div className="min-h-0 flex-1 overflow-y-auto">

            {error && (

              <div className="m-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs leading-5 text-rose-700">
                {error}
              </div>

            )}


            {activeTab ===
            "draft" ? (

              drafts.length ===
              0 ? (

                <div className="px-5 py-12 text-center">

                  <p className="text-sm font-medium text-slate-700">
                    No saved drafts
                  </p>

                  <p className="mt-1 text-xs text-slate-400">
                    Draft messages will appear here.
                  </p>

                </div>

              ) : (

                <div className="divide-y divide-slate-100">

                  {drafts.map(
                    (draft) => (

                      <button
                        type="button"
                        key={
                          draft.id
                        }
                        onClick={() =>
                          openDraft(
                            draft
                          )
                        }
                        className="block w-full px-4 py-3.5 text-left transition hover:bg-slate-50"
                      >

                        <p className="truncate text-sm font-semibold text-slate-900">
                          {draft.subject ||
                            "No Subject"}
                        </p>

                        <p className="mt-1 truncate text-xs text-slate-500">
                          {draft.recipients ||
                            "No recipient"}
                        </p>

                        <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                          Draft
                        </p>

                      </button>

                    )
                  )}

                </div>

              )

            ) : loading ? (

              <div className="px-5 py-12 text-center">

                <div className="mx-auto h-7 w-7 animate-pulse rounded-full bg-slate-200" />

                <p className="mt-3 text-xs font-medium text-slate-500">
                  Loading conversations...
                </p>

              </div>

            ) : conversations.length ===
              0 ? (

              <div className="px-5 py-12 text-center">

                <p className="text-sm font-medium text-slate-700">
                  No conversations found
                </p>

                <p className="mt-1 text-xs text-slate-400">
                  Try another mailbox, folder or search.
                </p>

              </div>

            ) : (

              <div className="divide-y divide-slate-100">

                {conversations.map(
                  (conversation) => {

                    const active =
                      conversation.conversation_id ===
                      selectedId;


                    const unread =
                      conversation.unread_count >
                      0;


                    return (

                      <div
                        key={
                          conversation.conversation_id
                        }
                        className={`group relative transition ${
                          active
                            ? "bg-slate-950"
                            : unread
                            ? "bg-sky-50/60 hover:bg-sky-50"
                            : "bg-white hover:bg-slate-50"
                        }`}
                      >

                        <button
                          type="button"
                          onClick={() =>
                            setSelectedId(
                              conversation.conversation_id
                            )
                          }
                          className="block w-full px-4 py-4 text-left"
                        >

                          <div className="flex items-start gap-3">

                            <input
                              type="checkbox"
                              checked={
                                selectedConversationIds.includes(
                                  conversation.conversation_id
                                )
                              }
                              onChange={() =>
                                toggleConversationSelection(
                                  conversation.conversation_id
                                )
                              }
                              onClick={(event) =>
                                event.stopPropagation()
                              }
                              className="mt-1 h-3.5 w-3.5 shrink-0 rounded border-slate-300"
                            />


                            <div className="min-w-0 flex-1">

                              <div className="flex items-start justify-between gap-2">

                                <p
                                  className={`truncate text-sm ${
                                    unread
                                      ? "font-bold"
                                      : "font-semibold"
                                  } ${
                                    active
                                      ? "text-white"
                                      : "text-slate-900"
                                  }`}
                                >
                                  {conversation.is_starred
                                    ? "? "
                                    : ""}
                                  {conversation.subject ||
                                    "No Subject"}
                                </p>


                                {unread && (

                                  <span
                                    className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-bold ${
                                      active
                                        ? "bg-white/15 text-white"
                                        : "bg-sky-100 text-sky-700"
                                    }`}
                                  >
                                    {conversation.unread_count}
                                  </span>

                                )}

                              </div>


                              {activeTab ===
                                "sent" && (

                                <p
                                  className={`mt-1 truncate text-xs ${
                                    active
                                      ? "text-slate-300"
                                      : "text-slate-500"
                                  }`}
                                >
                                  To:{" "}
                                  {conversation.recipients ||
                                    "Unknown recipient"}
                                </p>

                              )}


                              <p
                                className={`mt-1 line-clamp-2 text-xs leading-5 ${
                                  active
                                    ? "text-slate-300"
                                    : "text-slate-500"
                                }`}
                              >
                                {conversation.preview ||
                                  "No preview available"}
                              </p>


                              <div className="mt-2 flex items-center justify-between gap-2">

                                <span
                                  className={`rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
                                    active
                                      ? "bg-white/10 text-slate-300"
                                      : conversation.platform ===
                                        "gmail"
                                      ? "bg-rose-50 text-rose-600"
                                      : "bg-sky-50 text-sky-700"
                                  }`}
                                >
                                  {conversation.platform ||
                                    "mail"}
                                </span>

                                {unread && (

                                  <span
                                    className={`h-1.5 w-1.5 rounded-full ${
                                      active
                                        ? "bg-sky-300"
                                        : "bg-sky-500"
                                    }`}
                                  />

                                )}

                              </div>

                            </div>

                          </div>

                        </button>

                      </div>

                    );

                  }
                )}

              </div>

            )}

          </div>

        </aside>


        {/* ===================================================
            CONVERSATION WORKSPACE
        ==================================================== */}

        <section className="flex min-h-[620px] min-w-0 flex-1 flex-col bg-slate-50/50 lg:min-h-0">

          {!selectedId &&
            activeTab !==
              "draft" ? (

            <div className="flex min-h-[540px] flex-1 items-center justify-center px-6 py-16">

              <div className="max-w-md text-center">

                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-white text-xl shadow-sm">
                  ?
                </div>

                <h3 className="mt-5 text-lg font-semibold tracking-tight text-slate-900">
                  Select a conversation
                </h3>

                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Open a conversation to review communication history, attachments and execution context.
                </p>

              </div>

            </div>

          ) : activeTab ===
            "draft" ? (

            <div className="flex min-h-[540px] flex-1 items-center justify-center px-6 py-16">

              <div className="max-w-md text-center">

                <h3 className="text-lg font-semibold text-slate-900">
                  Draft workspace
                </h3>

                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Select a draft from the mailbox rail or create a new message.
                </p>

              </div>

            </div>

          ) : (

            <div className="flex min-h-0 flex-1 flex-col">

              {/* =============================================
                  CONVERSATION HEADER
              ============================================== */}

              <div className="border-b border-slate-200 bg-white px-4 py-4 sm:px-5 lg:px-6">

                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">

                  <div className="min-w-0">

                    <div className="flex flex-wrap items-center gap-2">

                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-500">
                        {messages[
                          messages.length -
                          1
                        ]?.platform ||
                          "mail"}
                      </span>

                      <span className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                        {messages.length} message
                        {messages.length ===
                        1
                          ? ""
                          : "s"}
                      </span>

                    </div>


                    <h2 className="mt-2 max-w-4xl truncate text-lg font-semibold tracking-tight text-slate-950 sm:text-xl">
                      {conversations.find(
                        (conversation) =>
                          conversation.conversation_id ===
                          selectedId
                      )?.subject ||
                        messages[
                          messages.length -
                          1
                        ]?.subject ||
                        "Conversation"}
                    </h2>

                  </div>


                  {messages.length >
                    0 && (

                    <div className="flex flex-wrap gap-1.5">

                      <button
                        type="button"
                        onClick={() => {

                          setError(
                            ""
                          );

                          setReplyMode(
                            "reply"
                          );

                          setShowReply(
                            true
                          );

                        }}
                        className="rounded-xl bg-slate-950 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
                      >
                        Reply
                      </button>


                      <button
                        type="button"
                        onClick={() => {

                          setError(
                            ""
                          );

                          setReplyMode(
                            "reply_all"
                          );

                          setShowReply(
                            true
                          );

                        }}
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Reply All
                      </button>


                      <button
                        type="button"
                        onClick={
                          beginForward
                        }
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Forward
                      </button>


                      <button
                        type="button"
                        onClick={
                          markConversationUnread
                        }
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        Mark unread
                      </button>


                      <button
                        type="button"
                        onClick={
                          toggleSelectedConversationStar
                        }
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        {conversations.find(
                          (conversation) =>
                            conversation.conversation_id ===
                            selectedId
                        )?.is_starred
                          ? "Unstar"
                          : "Star"}
                      </button>


                      <button
                        type="button"
                        onClick={
                          openSelectedMessageInProvider
                        }
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        {messages[
                          messages.length -
                          1
                        ]?.platform ===
                        "gmail"
                          ? "Open Gmail"
                          : messages[
                              messages.length -
                              1
                            ]?.platform ===
                            "outlook"
                          ? "Open Outlook"
                          : "Open Provider"}
                      </button>


                      <button
                        type="button"
                        onClick={
                          trashSelectedConversation
                        }
                        className="rounded-xl border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                      >
                        Trash
                      </button>

                    </div>

                  )}

                </div>

              </div>


              <div className="grid min-h-0 flex-1 xl:grid-cols-[minmax(0,1fr)_320px]">

                {/* ===========================================
                    MESSAGE THREAD
                ============================================ */}

                <div className="min-h-0 overflow-y-auto px-4 py-5 sm:px-5 lg:px-6">

                  {messages.length ===
                  0 ? (

                    <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
                      No messages found in this conversation.
                    </div>

                  ) : (

                    <div className="space-y-4">

                      {messages.map(
                        (message) => {

                          const outbound =
                            message.direction ===
                            "outbound";


                          return (

                            <article
                              key={
                                message.id
                              }
                              className={`overflow-hidden rounded-[24px] border shadow-sm ${
                                outbound
                                  ? "border-indigo-100 bg-indigo-50/35"
                                  : "border-slate-200 bg-white"
                              }`}
                            >

                              <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-start sm:justify-between">

                                <div className="min-w-0">

                                  <div className="flex flex-wrap items-center gap-2">

                                    <p className="truncate text-sm font-semibold text-slate-900">

                                      {outbound
                                        ? (
                                            "To: " +
                                            (
                                              message.recipients ||
                                              "Unknown recipient"
                                            )
                                          )
                                        : (
                                            message.sender ||
                                            "Unknown sender"
                                          )}

                                    </p>

                                    <span
                                      className={`rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
                                        outbound
                                          ? "bg-indigo-100 text-indigo-700"
                                          : "bg-slate-100 text-slate-600"
                                      }`}
                                    >
                                      {outbound
                                        ? "Sent"
                                        : "Received"}
                                    </span>

                                  </div>

                                  <p className="mt-1 text-xs text-slate-500">
                                    {message.subject ||
                                      "No Subject"}
                                  </p>

                                </div>


                                <div className="flex shrink-0 items-center gap-2 text-[10px] font-medium text-slate-400">

                                  <span className="uppercase">
                                    {message.platform ||
                                      "mail"}
                                  </span>

                                  {message.time && (

                                    <span>
                                      {new Date(
                                        message.time
                                      ).toLocaleString()}
                                    </span>

                                  )}

                                </div>

                              </div>


                              <div className="whitespace-pre-wrap break-words px-5 py-5 text-sm leading-7 text-slate-700">
                                {message.body ||
                                  "(No content)"}
                              </div>

                            </article>

                          );

                        }
                      )}

                    </div>

                  )}


                  {/* =========================================
                      ATTACHMENTS
                  ========================================== */}

                  {attachments.length >
                    0 && (

                    <section className="mt-6 rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm sm:p-5">

                      <div className="mb-3 flex items-center justify-between gap-3">

                        <div>

                          <p className="text-sm font-semibold text-slate-900">
                            Attachments
                          </p>

                          <p className="mt-0.5 text-xs text-slate-400">
                            {attachments.length} file
                            {attachments.length ===
                            1
                              ? ""
                              : "s"}{" "}
                            available
                          </p>

                        </div>

                      </div>


                      <div className="grid gap-2 sm:grid-cols-2">

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
                              className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-3"
                            >

                              <div className="min-w-0">

                                <p className="truncate text-xs font-semibold text-slate-800">
                                  {attachment.filename ||
                                    "Attachment"}
                                </p>

                                <p className="mt-0.5 truncate text-[10px] text-slate-400">
                                  {attachment.mime_type ||
                                    "File attachment"}
                                </p>

                              </div>


                              <button
                                type="button"
                                disabled={
                                  attachment.downloadable ===
                                  false
                                }
                                onClick={() =>
                                  downloadFile(
                                    attachment.message_id,
                                    attachment.attachment_id,
                                    attachment.filename
                                  )
                                }
                                className="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {attachment.downloadable ===
                                false
                                  ? "Unavailable"
                                  : "Download"}
                              </button>

                            </div>

                          )
                        )}

                      </div>

                    </section>

                  )}

                </div>


                {/* ===========================================
                    ACCOUNTABILITY TIMELINE
                ============================================ */}

                <aside className="min-h-0 border-t border-slate-200 bg-white xl:border-l xl:border-t-0">

                  <ConversationTimeline
                    conversationId={
                      selectedId
                    }
                  />

                </aside>

              </div>

            </div>

          )}

        </section>

      </div>


      {/* =====================================================
          COMPOSE MODAL
      ====================================================== */}

      {showCompose && (

        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-[2px]">

          <div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-[26px] border border-slate-200 bg-white shadow-2xl">

            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-100 bg-white px-5 py-4 sm:px-6">

              <div>

                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                  {forwardSourceId
                    ? "Existing communication"
                    : activeDraftId
                    ? "Saved message"
                    : "New communication"}
                </p>

                <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                  {forwardSourceId
                    ? "Forward Message"
                    : activeDraftId
                    ? "Edit Draft"
                    : "Compose"}
                </h3>

              </div>


              <button
                type="button"
                onClick={
                  closeCompose
                }
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-50"
              >
                Close
              </button>

            </div>


            <div className="space-y-4 px-5 py-5 sm:px-6">

              {forwardSourceId && (

                <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs leading-5 text-amber-800">

                  Forwarding remains bound to the original mailbox.

                  {attachments.some(
                    (attachment) =>
                      attachment.message_id ===
                      forwardSourceId
                  )
                    ? " Original attachments are not automatically forwarded; download them or use Open in Provider when attachment forwarding is required."
                    : ""}

                </div>

              )}


              <div>

                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  From
                </label>

                <select
                  value={
                    composeAccountId
                  }
                  disabled={
                    Boolean(
                      forwardSourceId
                    )
                  }
                  onChange={(event) =>
                    setComposeAccountId(
                      event.target.value
                    )
                  }
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100 disabled:bg-slate-50 disabled:text-slate-500"
                >
                  <option value="">
                    Select sending account
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
                        {account.email_address}
                        {" ? "}
                        {account.account_type
                          ?.toUpperCase()}
                      </option>

                    )
                  )}
                </select>

              </div>


              <RecipientChipInput
                label="To"
                value={
                  composeData.to
                }
                onChange={
                  (recipients) =>
                    setComposeData(
                      (current) => ({
                        ...current,
                        to:
                          recipients,
                      })
                    )
                }
                placeholder="Type a name or email"
              />


              <div className="grid gap-3 sm:grid-cols-2">

                <RecipientChipInput
                  label="Cc"
                  value={
                    composeData.cc
                  }
                  onChange={
                    (recipients) =>
                      setComposeData(
                        (current) => ({
                          ...current,
                          cc:
                            recipients,
                        })
                      )
                  }
                  placeholder="Add Cc recipients"
                />


                <RecipientChipInput
                  label="Bcc"
                  value={
                    composeData.bcc
                  }
                  onChange={
                    (recipients) =>
                      setComposeData(
                        (current) => ({
                          ...current,
                          bcc:
                            recipients,
                        })
                      )
                  }
                  placeholder="Add Bcc recipients"
                />

              </div>


              <p className="-mt-2 text-[10px] text-slate-400">
                Recipient suggestions are ranked from communication history.
              </p>


              <div>

                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  Subject
                </label>

                <input
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
                  placeholder="Message subject"
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
                />

              </div>


              <div>

                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  Message
                </label>

                <textarea
                  rows={10}
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
                  placeholder="Write your message..."
                  className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
                />

              </div>

            </div>


            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 bg-slate-50/70 px-5 py-4 sm:px-6">

              {!forwardSourceId && (

                <button
                  type="button"
                  onClick={
                    saveDraft
                  }
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Save draft
                </button>

              )}


              {activeDraftId ? (

                <button
                  type="button"
                  onClick={
                    sendDraft
                  }
                  className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
                >
                  Send draft
                </button>

              ) : (

                <button
                  type="button"
                  onClick={
                    sendEmail
                  }
                  className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
                >
                  {forwardSourceId
                    ? "Forward"
                    : "Send message"}
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

        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-[2px]">

          <div className="w-full max-w-xl overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-2xl">

            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">

              <div>

                <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                  Conversation response
                </p>

                <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                  {replyMode ===
                  "reply_all"
                    ? "Reply All"
                    : "Reply"}
                </h3>

              </div>


              <button
                type="button"
                disabled={
                  replying
                }
                onClick={() => {

                  if (!replying) {

                    setShowReply(
                      false
                    );

                    setReplyBody(
                      ""
                    );

                  }

                }}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-50 disabled:opacity-50"
              >
                Close
              </button>

            </div>


            <div className="px-5 py-5">

              <textarea
                rows={9}
                value={
                  replyBody
                }
                onChange={(event) =>
                  setReplyBody(
                    event.target.value
                  )
                }
                placeholder="Write your reply..."
                disabled={
                  replying
                }
                className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-100 disabled:bg-slate-50"
              />

            </div>


            <div className="flex justify-end gap-2 border-t border-slate-100 bg-slate-50/70 px-5 py-4">

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
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
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
                className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {replying
                  ? "Sending..."
                  : replyMode ===
                    "reply_all"
                  ? "Send Reply All"
                  : "Send Reply"}
              </button>

            </div>

          </div>

        </div>

      )}

    </div>

  );

}
