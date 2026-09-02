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


const createOutboundIdempotencyKey = () => {

  if (
    globalThis.crypto
      ?.randomUUID
  ) {

    return (
      "mail-" +
      globalThis.crypto.randomUUID()
    );

  }


  return (
    "mail-" +
    Date.now() +
    "-" +
    Math.random()
      .toString(16)
      .slice(2)
  );

};


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

  const [
    forwardSourceAttachments,
    setForwardSourceAttachments,
  ] = useState([]);

  const [
    composeFiles,
    setComposeFiles,
  ] = useState([]);

  const [
    composeSending,
    setComposeSending,
  ] = useState(false);

  const composeSendLockRef =
    useRef(false);

  const composeIdempotencyKeyRef =
    useRef("");


  // ==========================================================
  // REPLY STATE
  // ==========================================================

  const [showReply, setShowReply] = useState(false);

  const [replyBody, setReplyBody] = useState("");

  const [replyMode, setReplyMode] = useState("reply");

  const [replying, setReplying] = useState(false);

  const replySendLockRef =
    useRef(false);

  const replyIdempotencyKeyRef =
    useRef("");

  const [
    replyFiles,
    setReplyFiles,
  ] = useState([]);


  // ==========================================================
  // DRAFT STATE
  // ==========================================================

  const [drafts, setDrafts] = useState([]);

  const [activeDraftId, setActiveDraftId] =
    useState(null);

  const [
    composePersistedAttachments,
    setComposePersistedAttachments,
  ] = useState([]);


  // ==========================================================
  // UI STATE
  // ==========================================================

  const [loading, setLoading] = useState(false);

  const [syncing, setSyncing] = useState("");

  const [error, setError] = useState("");

  const [
    conversationMeta,
    setConversationMeta,
  ] = useState({
    count: 0,
    currentPage: 1,
    totalPages: 1,
  });

  const [
    loadingMore,
    setLoadingMore,
  ] = useState(false);

  const [
    syncNotice,
    setSyncNotice,
  ] = useState("");

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

      setSelectedAccountId((currentId) => {

        if (!currentId) {
          return "";
        }

        const stillConnected =
          data.some(
            (account) =>
              String(account.id) ===
              String(currentId)
          );

        return stillConnected
          ? currentId
          : "";

      });

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

      const response =
        await axios.get(
          "/api/inbox/sync-status/"
        );

      const data =
        response.data || [];

      setSyncStatuses(
        data
      );

      return data;

    } catch (err) {

      console.error(
        "Sync status error:",
        err
      );

      return [];

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

    const item =
      getSyncStatus(
        platform
      );

    if (!item) {
      return "Not synced";
    }

    if (
      item.status ===
      "syncing"
    ) {

      return (
        `Syncing ${item.progress || 0}%`
      );

    }

    if (
      item.status ===
      "failed"
    ) {
      return "Sync failed";
    }

    if (
      item.last_synced_at
    ) {

      return (
        `Synced ${new Date(
          item.last_synced_at
        ).toLocaleString()}`
      );

    }

    return (
      item.status ||
      "Not synced"
    );

  };


  // ==========================================================
  // LOAD CONVERSATIONS
  // ==========================================================

  const loadConversations =
    useCallback(async (
      options = {}
    ) => {

      const requestedPage =
        Number(
          options.page || 1
        );

      const append =
        Boolean(
          options.append
        );


      if (
        activeTab ===
        "draft"
      ) {

        setConversations([]);

        setConversationMeta({
          count: 0,
          currentPage: 1,
          totalPages: 1,
        });

        setLoading(false);

        return;
      }


      try {

        setError("");

        if (append) {

          setLoadingMore(
            true
          );

        } else {

          setLoading(
            true
          );

        }


        const queryParams =
          new URLSearchParams({
            folder:
              activeTab,

            page:
              String(
                requestedPage
              ),

            page_size:
              "30",
          });


        if (
          search.trim()
        ) {

          queryParams.set(
            "search",
            search.trim()
          );

        }


        if (
          selectedAccountId
        ) {

          queryParams.set(
            "account_id",
            selectedAccountId
          );

        }


        const response =
          await axios.get(
            `/api/inbox/unified-conversations/?${queryParams.toString()}`
          );


        const data =
          response.data?.results ||
          [];


        setConversationMeta({
          count:
            Number(
              response.data?.count ||
              0
            ),

          currentPage:
            Number(
              response.data?.current_page ||
              requestedPage
            ),

          totalPages:
            Number(
              response.data?.total_pages ||
              1
            ),
        });


        if (append) {

          setConversations(
            (current) => {

              const seen =
                new Set(
                  current.map(
                    (conversation) =>
                      conversation
                        .conversation_id
                  )
                );


              const next = [
                ...current,
              ];


              for (
                const conversation
                of data
              ) {

                if (
                  seen.has(
                    conversation
                      .conversation_id
                  )
                ) {
                  continue;
                }


                seen.add(
                  conversation
                    .conversation_id
                );


                next.push(
                  conversation
                );

              }


              return next;

            }
          );


          return;
        }


        setConversations(
          data
        );


        const urlParams =
          new URLSearchParams(
            location.search
          );


        const conversationFromUrl =
          urlParams.get(
            "conversation"
          );


        if (
          data.length ===
          0
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

          return;
        }


        if (
          conversationFromUrl
        ) {

          const match =
            data.find(
              (conversation) =>
                String(
                  conversation
                    .conversation_id
                ) ===
                String(
                  conversationFromUrl
                )
            );


          if (match) {

            setSelectedId(
              match
                .conversation_id
            );

            return;

          }

        }


        setSelectedId(
          (currentId) => {

            const stillExists =
              data.some(
                (conversation) =>
                  conversation
                    .conversation_id ===
                  currentId
              );


            if (
              stillExists
            ) {
              return currentId;
            }


            return (
              data[0]
                .conversation_id
            );

          }
        );

      } catch (err) {

        console.error(
          "Load conversations error:",
          err
        );


        setError(
          "Unable to load conversations."
        );

      } finally {

        if (append) {

          setLoadingMore(
            false
          );

        } else {

          setLoading(
            false
          );

        }

      }

    }, [
      activeTab,
      location.search,
      search,
      selectedAccountId,
    ]);


  const loadMoreConversations =
    async () => {

      if (
        loadingMore ||
        conversationMeta
          .currentPage >=
        conversationMeta
          .totalPages
      ) {
        return;
      }


      await loadConversations({
        page:
          conversationMeta
            .currentPage +
          1,

        append:
          true,
      });

    };


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
  // OUTBOUND ATTACHMENT HELPERS
  // ==========================================================

  const formatComposeFileSize =
    (size) => {

      if (
        size >=
        1024 * 1024
      ) {

        return `${(
          size /
          (1024 * 1024)
        ).toFixed(1)} MB`;

      }


      return `${Math.max(
        1,
        Math.ceil(
          size / 1024
        )
      )} KB`;

    };


  const selectedComposeAccount =
    accounts.find(
      (account) =>
        String(
          account.id
        ) ===
        String(
          composeAccountId
        )
    );


  const composeAttachmentLimitBytes =
    selectedComposeAccount
      ?.account_type ===
      "outlook"
        ? 3 * 1024 * 1024
        : 18 * 1024 * 1024;


  const handleComposeFiles =
    (event) => {

      const selected =
        Array.from(
          event.target.files ||
          []
        );


      event.target.value =
        "";


      if (!composeAccountId) {

        setError(
          "Select the sending mailbox before adding attachments."
        );

        return;

      }


      const next = [
        ...composeFiles,
        ...selected,
      ];


      const totalCount =
        composePersistedAttachments.length +
        forwardSourceAttachments.length +
        next.length;


      if (
        totalCount >
        10
      ) {

        setError(
          "A maximum of 10 attachments can be sent at once."
        );

        return;

      }


      const persistedTotal =
        composePersistedAttachments.reduce(
          (
            current,
            attachment
          ) =>
            current +
            Number(
              attachment.size ||
              0
            ),
          0
        );


      const forwardedTotal =
        forwardSourceAttachments.reduce(
          (
            current,
            attachment
          ) =>
            current +
            Number(
              attachment.size ||
              0
            ),
          0
        );


      const newTotal =
        next.reduce(
          (
            current,
            file
          ) =>
            current +
            Number(
              file.size ||
              0
            ),
          0
        );


      if (
        persistedTotal +
        forwardedTotal +
        newTotal >
        composeAttachmentLimitBytes
      ) {

        const limitMb =
          selectedComposeAccount
            ?.account_type ===
            "outlook"
              ? 3
              : 18;


        setError(
          `Attachments exceed the ${limitMb} MB outbound limit for this mailbox.`
        );

        return;

      }


      setError("");

      setComposeFiles(
        next
      );

    };


  const removeComposeFile =
    (index) => {

      setComposeFiles(
        (current) =>
          current.filter(
            (
              _file,
              fileIndex
            ) =>
              fileIndex !==
              index
          )
      );

    };


  const removePersistedDraftAttachment =
    (attachmentId) => {

      setComposePersistedAttachments(
        (current) =>
          current.filter(
            (attachment) =>
              String(
                attachment.id
              ) !==
              String(
                attachmentId
              )
          )
      );

    };


  const removeForwardSourceAttachment =
    (attachmentKey) => {

      setForwardSourceAttachments(
        (current) =>
          current.filter(
            (attachment) =>
              attachment.key !==
              attachmentKey
          )
      );

    };


  // ==========================================================
  // REPLY ATTACHMENT HELPERS
  // ==========================================================

  const replySourceMessage =
    messages.length > 0
      ? messages[
          messages.length - 1
        ]
      : null;


  const replySourceAccount =
    accounts.find(
      (account) =>
        String(
          account.id
        ) ===
        String(
          replySourceMessage
            ?.email_account_id ||
          ""
        )
    );


  const replyAttachmentLimitBytes =
    replySourceAccount
      ?.account_type ===
      "outlook"
        ? 3 * 1024 * 1024
        : 18 * 1024 * 1024;


  const handleReplyFiles =
    (event) => {

      const selected =
        Array.from(
          event.target.files ||
          []
        );


      event.target.value =
        "";


      if (
        !replySourceAccount ||
        ![
          "gmail",
          "outlook",
        ].includes(
          replySourceAccount
            .account_type
        )
      ) {

        setError(
          "Reply attachments are available for Gmail and Microsoft 365."
        );

        return;

      }


      const next = [
        ...replyFiles,
        ...selected,
      ];


      if (
        next.length >
        10
      ) {

        setError(
          "A maximum of 10 attachments can be sent at once."
        );

        return;

      }


      const total =
        next.reduce(
          (
            current,
            file
          ) =>
            current +
            Number(
              file.size ||
              0
            ),
          0
        );


      if (
        total >
        replyAttachmentLimitBytes
      ) {

        const limitMb =
          replySourceAccount
            .account_type ===
            "outlook"
              ? 3
              : 18;


        setError(
          `Attachments exceed the ${limitMb} MB outbound limit for this mailbox.`
        );

        return;

      }


      setError("");

      setReplyFiles(
        next
      );

    };


  const removeReplyFile =
    (index) => {

      setReplyFiles(
        (current) =>
          current.filter(
            (
              _file,
              fileIndex
            ) =>
              fileIndex !==
              index
          )
      );

    };


  // ==========================================================
  // SEND EMAIL
  // ==========================================================

  const sendEmail = async () => {

    if (
      composeSendLockRef.current
    ) {
      return;
    }


    if (
      composeData.to.length === 0
    ) {

      setError(
        "Add at least one recipient."
      );

      return;
    }


    if (!composeAccountId) {

      setError(
        "Select the sending mailbox."
      );

      return;
    }


    composeSendLockRef.current =
      true;

    setComposeSending(
      true
    );


    if (
      !composeIdempotencyKeyRef
        .current
    ) {

      composeIdempotencyKeyRef.current =
        createOutboundIdempotencyKey();

    }


    const idempotencyKey =
      composeIdempotencyKeyRef.current;


    try {

      setError("");


      const sendEndpoint =
        forwardSourceId
          ? `/api/inbox/message/${forwardSourceId}/forward/`
          : "/api/inbox/send/";


      const requestConfig = {
        headers: {
          "Idempotency-Key":
            idempotencyKey,
        },
      };


      if (
        composeFiles.length >
        0
        ||
        Boolean(
          forwardSourceId
        )
      ) {

        const formData =
          new FormData();


        formData.append(
          "to",
          serializeRecipients(
            composeData.to
          )
        );

        formData.append(
          "cc",
          serializeRecipients(
            composeData.cc
          )
        );

        formData.append(
          "bcc",
          serializeRecipients(
            composeData.bcc
          )
        );

        formData.append(
          "subject",
          composeData.subject
        );

        formData.append(
          "body",
          composeData.body
        );

        formData.append(
          "account_id",
          composeAccountId
        );


        if (forwardSourceId) {

          formData.append(
            "source_attachment_keys",
            JSON.stringify(
              forwardSourceAttachments.map(
                (attachment) =>
                  attachment.key
              )
            )
          );

        }


        for (
          const file
          of composeFiles
        ) {

          formData.append(
            "attachments",
            file,
            file.name
          );

        }


        await axios.post(
          sendEndpoint,
          formData,
          requestConfig
        );


      } else {

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
          },
          requestConfig
        );

      }


      composeIdempotencyKeyRef.current =
        "";


      setShowCompose(false);

      setActiveDraftId(null);

      setForwardSourceId(null);

      setForwardSourceAttachments([]);

      setComposeFiles([]);

      setComposePersistedAttachments([]);


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


      // Keep the same key after a network/provider uncertainty.
      // A manual retry therefore asks the backend for the same
      // semantic send rather than creating another message.
      setError(
        err.response?.data?.error ||
          "Unable to send email."
      );


    } finally {

      composeSendLockRef.current =
        false;

      setComposeSending(
        false
      );

    }

  };


  // ==========================================================
  // SEND REPLY
  // ==========================================================

  const sendReply = async () => {

    if (
      replySendLockRef.current
    ) {
      return;
    }


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


    replySendLockRef.current =
      true;


    if (
      !replyIdempotencyKeyRef
        .current
    ) {

      replyIdempotencyKeyRef.current =
        createOutboundIdempotencyKey();

    }


    const idempotencyKey =
      replyIdempotencyKeyRef.current;


    try {

      setError("");

      setReplying(true);


      const endpoint =
        `/api/inbox/conversations/${selectedId}/reply/`;


      const requestConfig = {
        headers: {
          "Idempotency-Key":
            idempotencyKey,
        },
      };


      if (
        replyFiles.length >
        0
      ) {

        const formData =
          new FormData();


        formData.append(
          "body",
          replyBody.trim()
        );

        formData.append(
          "mode",
          replyMode
        );


        for (
          const file
          of replyFiles
        ) {

          formData.append(
            "attachments",
            file,
            file.name
          );

        }


        await axios.post(
          endpoint,
          formData,
          requestConfig
        );

      } else {

        await axios.post(
          endpoint,
          {
            body:
              replyBody.trim(),

            mode:
              replyMode,
          },
          requestConfig
        );

      }


      replyIdempotencyKeyRef.current =
        "";


      setReplyBody("");

      setReplyFiles([]);

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

      replySendLockRef.current =
        false;

      setReplying(false);

    }

  };


  // ==========================================================
  // SAVE DRAFT
  // ==========================================================

  const persistCurrentDraft =
    async () => {

      if (!composeAccountId) {

        throw new Error(
          "Select the sending mailbox."
        );

      }


      const formData =
        new FormData();


      if (activeDraftId) {

        formData.append(
          "draft_id",
          activeDraftId
        );

      }


      if (selectedId) {

        formData.append(
          "conversation_id",
          selectedId
        );

      }


      formData.append(
        "subject",
        composeData.subject
      );

      formData.append(
        "body",
        composeData.body
      );

      formData.append(
        "recipients",
        serializeRecipients(
          composeData.to
        )
      );

      formData.append(
        "to",
        serializeRecipients(
          composeData.to
        )
      );

      formData.append(
        "cc",
        serializeRecipients(
          composeData.cc
        )
      );

      formData.append(
        "bcc",
        serializeRecipients(
          composeData.bcc
        )
      );

      formData.append(
        "account_id",
        composeAccountId
      );

      formData.append(
        "retained_attachment_ids",
        JSON.stringify(
          composePersistedAttachments.map(
            (attachment) =>
              attachment.id
          )
        )
      );


      for (
        const file
        of composeFiles
      ) {

        formData.append(
          "attachments",
          file,
          file.name
        );

      }


      const response =
        await axios.post(
          "/api/inbox/draft/save/",
          formData
        );


      return response.data;

    };


  const saveDraft = async () => {

    try {

      setError("");


      await persistCurrentDraft();


      setShowCompose(false);

      setActiveDraftId(null);

      setSelectedId(null);

      setComposeFiles([]);

      setComposePersistedAttachments([]);


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
          err.message ||
          "Unable to save draft."
      );

    }

  };


  // ==========================================================
  // SEND DRAFT
  // ==========================================================

  const sendDraft = async () => {

    if (
      composeSendLockRef.current
    ) {
      return;
    }


    if (!activeDraftId) {

      setError(
        "No draft selected."
      );

      return;
    }


    composeSendLockRef.current =
      true;

    setComposeSending(
      true
    );


    try {

      setError("");


      const saved =
        await persistCurrentDraft();


      const savedDraftId =
        saved?.draft_id ||
        activeDraftId;


      await axios.post(
        `/api/inbox/draft/send/${savedDraftId}/`
      );


      composeIdempotencyKeyRef.current =
        "";


      setShowCompose(false);

      setActiveDraftId(null);

      setSelectedId(null);

      setComposeFiles([]);

      setComposePersistedAttachments([]);


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
          err.message ||
          "Unable to send draft."
      );


    } finally {

      composeSendLockRef.current =
        false;

      setComposeSending(
        false
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
        provider ===
        "gmail"
          ? "/api/google/oauth/sync/"
          : "/api/microsoft/oauth/sync/";


      const providerLabel =
        provider ===
        "gmail"
          ? "Gmail"
          : "Microsoft 365";


      const previous =
        getSyncStatus(
          provider
        );


      const previousLastSync =
        previous
          ?.last_synced_at ||
        "";


      try {

        setError("");

        setSyncing(
          provider
        );

        setSyncNotice(
          `${providerLabel} sync queued...`
        );


        const queued =
          await axios.post(
            endpoint
          );


        if (
          queued.status !==
          202
        ) {

          throw new Error(
            "Mailbox synchronization was not queued."
          );

        }


        let completed =
          false;


        for (
          let attempt = 0;
          attempt < 60;
          attempt += 1
        ) {

          await new Promise(
            (resolve) =>
              window.setTimeout(
                resolve,
                1000
              )
          );


          const statuses =
            await loadSyncStatus();


          const current =
            statuses.find(
              (item) =>
                item.platform ===
                provider
            );


          if (!current) {
            continue;
          }


          if (
            current.status ===
            "failed"
          ) {

            throw new Error(
              current.error_message ||
              `${providerLabel} synchronization failed.`
            );

          }


          if (
            current.status ===
            "syncing"
          ) {

            setSyncNotice(
              `${providerLabel} syncing ${current.progress || 0}%...`
            );

            continue;

          }


          const completedAt =
            current
              .last_synced_at;


          if (
            current.status ===
              "success" &&
            completedAt &&
            (
              !previousLastSync ||
              completedAt !==
                previousLastSync
            )
          ) {

            completed =
              true;


            setSyncNotice(
              `${providerLabel} synced ${new Date(
                completedAt
              ).toLocaleString()}`
            );


            await loadConversations({
              page: 1,
              append: false,
            });


            break;

          }

        }


        if (!completed) {

          setSyncNotice(
            `${providerLabel} sync is still running. Refresh will occur when a completion event is received.`
          );

        }

      } catch (err) {

        console.error(
          "Sync error:",
          err
        );


        setError(
          err.response?.data?.error ||
          err.message ||
          `Unable to sync ${providerLabel}.`
        );


        setSyncNotice(
          `${providerLabel} sync did not complete successfully.`
        );


        await loadSyncStatus();

      } finally {

        setSyncing(
          ""
        );

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


  const beginForward = async () => {

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


    try {

      setError("");

      composeIdempotencyKeyRef.current =
        "";

      setActiveDraftId(null);

      setComposeFiles([]);

      setComposePersistedAttachments([]);


      const preflight =
        await axios.get(
          `/api/inbox/message/${latestMessage.id}/forward/`
        );


      const inherited =
        Array.isArray(
          preflight.data?.source_attachments
        )
          ? preflight.data.source_attachments
          : [];


      setForwardSourceAttachments(
        inherited
      );


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


    } catch (err) {

      console.error(
        "Forward preflight error:",
        err
      );


      setForwardSourceAttachments(
        []
      );


      setError(
        err.response?.data?.error ||
          "Unable to prepare this message for forwarding."
      );

    }

  };


  // ==========================================================
  // OPEN DRAFT
  // ==========================================================

  const openDraft = (draft) => {

    setError("");

    composeIdempotencyKeyRef.current =
      "";

    setComposeFiles([]);

    setComposePersistedAttachments(
      Array.isArray(
        draft.attachments
      )
        ? draft.attachments
        : []
    );

    setForwardSourceId(null);

    setForwardSourceAttachments([]);

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

    composeIdempotencyKeyRef.current =
      "";

    setShowCompose(false);

    setActiveDraftId(null);

    setForwardSourceId(null);

    setForwardSourceAttachments([]);

    setComposeFiles([]);

    setComposePersistedAttachments([]);


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

                  setComposeFiles([]);

                  setComposePersistedAttachments([]);

                  setForwardSourceId(
                    null
                  );

                  setForwardSourceAttachments(
                    []
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

                  composeIdempotencyKeyRef.current =
                    "";

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
                COMPACT PROVIDER HEALTH
            ============================================== */}

            <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2.5">

              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">

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
                        className="flex min-w-0 items-center gap-2"
                      >

                        <span
                          className={`h-2 w-2 shrink-0 rounded-full ${
                            connected
                              ? "bg-emerald-500"
                              : "bg-slate-300"
                          }`}
                        />


                        <span className="text-[11px] font-semibold text-slate-700">
                          {provider.label}
                        </span>


                        <span className="max-w-[180px] truncate text-[10px] text-slate-400">
                          {formatSyncStatus(
                            provider.provider
                          )}
                        </span>


                        {!connected ? (

                          <button
                            type="button"
                            onClick={() =>
                              connectProvider(
                                provider.provider
                              )
                            }
                            className="text-[10px] font-semibold text-slate-600 hover:text-slate-950"
                          >
                            Connect
                          </button>

                        ) : (

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
                            className="text-[10px] font-semibold text-slate-600 hover:text-slate-950 disabled:cursor-wait disabled:opacity-50"
                          >
                            {busy
                              ? "Syncing..."
                              : "Sync"}
                          </button>

                        )}

                      </div>

                    );

                  }
                )}

              </div>


              {syncNotice && (

                <p className="mt-2 border-t border-slate-200 pt-2 text-[10px] leading-4 text-slate-500">
                  {syncNotice}
                </p>

              )}

            </div>


            {/* =============================================
                ACCOUNT FILTER
            ============================================== */}

            <div className="mt-3">

              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                View mailbox
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
                  placeholder={
                    selectedAccountId
                      ? "Search this mailbox..."
                      : "Search all connected mailboxes..."
                  }
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

                  <span className="mr-auto text-[10px] font-medium text-slate-400">
                    Showing {conversations.length} of {conversationMeta.count}
                  </span>

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


                {conversationMeta.currentPage <
                  conversationMeta.totalPages && (

                  <div className="bg-white px-4 py-4 text-center">

                    <button
                      type="button"
                      disabled={
                        loadingMore
                      }
                      onClick={
                        loadMoreConversations
                      }
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-wait disabled:opacity-50"
                    >
                      {loadingMore
                        ? "Loading older conversations..."
                        : "Load older conversations"}
                    </button>


                    <p className="mt-2 text-[10px] text-slate-400">
                      {conversations.length} of {conversationMeta.count} loaded
                    </p>

                  </div>

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

                          replyIdempotencyKeyRef.current =
                            "";

                          setReplyMode(
                            "reply"
                          );

                          setReplyFiles([]);

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

                          replyIdempotencyKeyRef.current =
                            "";

                          setReplyMode(
                            "reply_all"
                          );

                          setReplyFiles([]);

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

                <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs leading-5 text-slate-600">

                  Forwarding remains bound to the original mailbox.

                  {forwardSourceAttachments.length > 0
                    ? ` ${forwardSourceAttachments.length} original attachment${forwardSourceAttachments.length === 1 ? "" : "s"} selected automatically.`
                    : " No original attachments are selected."}

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


              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">

                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">

                  <div>

                    <p className="text-sm font-semibold text-slate-800">
                      Attach files
                    </p>

                    <p className="mt-1 text-[11px] leading-5 text-slate-500">
                      Up to 10 files. Gmail: 18 MB total. Microsoft 365: 3 MB total.
                    </p>

                  </div>


                  <label className="inline-flex cursor-pointer items-center justify-center rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50">

                    Add files

                    <input
                      type="file"
                      multiple
                      onChange={
                        handleComposeFiles
                      }
                      className="hidden"
                    />

                  </label>

                </div>


                {activeDraftId && (

                  <p className="mt-3 text-[11px] leading-5 text-slate-500">
                    Saved draft files stay attached when you close and reopen this draft.
                  </p>

                )}


                {composePersistedAttachments.length > 0 && (

                  <div className="mt-3 space-y-2">

                    {composePersistedAttachments.map(
                      (attachment) => (

                        <div
                          key={`saved-${attachment.id}`}
                          className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5"
                        >

                          <div className="min-w-0">

                            <p className="truncate text-xs font-semibold text-slate-700">
                              {attachment.filename}
                            </p>

                            <p className="mt-0.5 text-[10px] text-slate-400">
                              Saved in draft
                              {" ? "}
                              {formatComposeFileSize(
                                attachment.size
                              )}
                            </p>

                          </div>


                          <button
                            type="button"
                            onClick={() =>
                              removePersistedDraftAttachment(
                                attachment.id
                              )
                            }
                            className="shrink-0 rounded-lg px-2 py-1 text-[10px] font-semibold text-rose-600 hover:bg-rose-50"
                          >
                            Remove
                          </button>

                        </div>

                      )
                    )}

                  </div>

                )}


                {forwardSourceId && (

                  <div className="mt-3">

                    <p className="text-[11px] leading-5 text-slate-500">
                      Original attachments are included automatically. Remove any file you do not want to forward.
                    </p>


                    {forwardSourceAttachments.length > 0 && (

                      <div className="mt-2 space-y-2">

                        {forwardSourceAttachments.map(
                          (attachment) => (

                            <div
                              key={`forward-source-${attachment.key}`}
                              className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5"
                            >

                              <div className="min-w-0">

                                <p className="truncate text-xs font-semibold text-slate-700">
                                  {attachment.filename ||
                                    "Attachment"}
                                </p>

                                <p className="mt-0.5 text-[10px] text-slate-400">
                                  Original attachment
                                  {Number(
                                    attachment.size ||
                                    0
                                  ) > 0
                                    ? ` ? ${formatComposeFileSize(
                                        Number(
                                          attachment.size
                                        )
                                      )}`
                                    : ""}
                                </p>

                              </div>


                              <button
                                type="button"
                                onClick={() =>
                                  removeForwardSourceAttachment(
                                    attachment.key
                                  )
                                }
                                className="shrink-0 rounded-lg px-2 py-1 text-[10px] font-semibold text-rose-600 hover:bg-rose-50"
                              >
                                Remove
                              </button>

                            </div>

                          )
                        )}

                      </div>

                    )}

                  </div>

                )}


                {composeFiles.length > 0 && (

                  <div className="mt-3 space-y-2">

                    {composeFiles.map(
                      (
                        file,
                        index
                      ) => (

                        <div
                          key={`${file.name}-${file.size}-${index}`}
                          className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5"
                        >

                          <div className="min-w-0">

                            <p className="truncate text-xs font-semibold text-slate-700">
                              {file.name}
                            </p>

                            <p className="mt-0.5 text-[10px] text-slate-400">
                              {formatComposeFileSize(
                                file.size
                              )}
                            </p>

                          </div>


                          <button
                            type="button"
                            onClick={() =>
                              removeComposeFile(
                                index
                              )
                            }
                            className="shrink-0 rounded-lg px-2 py-1 text-[10px] font-semibold text-rose-600 hover:bg-rose-50"
                          >
                            Remove
                          </button>

                        </div>

                      )
                    )}

                  </div>

                )}

              </div>


            </div>


            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 bg-slate-50/70 px-5 py-4 sm:px-6">

              {!forwardSourceId && (

                <button
                  type="button"
                  onClick={
                    saveDraft
                  }
                  disabled={
                    composeSending
                  }
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
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
                  disabled={
                    composeSending
                  }
                  className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {composeSending
                    ? "Sending..."
                    : "Send draft"}
                </button>

              ) : (

                <button
                  type="button"
                  onClick={
                    sendEmail
                  }
                  disabled={
                    composeSending
                  }
                  className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {composeSending
                    ? "Sending..."
                    : forwardSourceId
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

                    replyIdempotencyKeyRef.current =
                      "";

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


            <div className="space-y-4 px-5 py-5">

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


              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">

                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">

                  <div>

                    <p className="text-sm font-semibold text-slate-800">
                      Attach files
                    </p>

                    <p className="mt-1 text-[11px] leading-5 text-slate-500">
                      Up to 10 files. Gmail: 18 MB total. Microsoft 365: 3 MB total.
                    </p>

                  </div>


                  <label
                    className={`inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm ${
                      replying
                        ? "cursor-not-allowed opacity-50"
                        : "cursor-pointer hover:bg-slate-50"
                    }`}
                  >

                    Add files

                    <input
                      type="file"
                      multiple
                      disabled={
                        replying
                      }
                      onChange={
                        handleReplyFiles
                      }
                      className="hidden"
                    />

                  </label>

                </div>


                {replyFiles.length > 0 && (

                  <div className="mt-3 space-y-2">

                    {replyFiles.map(
                      (
                        file,
                        index
                      ) => (

                        <div
                          key={`${file.name}-${file.size}-${index}`}
                          className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5"
                        >

                          <div className="min-w-0">

                            <p className="truncate text-xs font-semibold text-slate-700">
                              {file.name}
                            </p>

                            <p className="mt-0.5 text-[10px] text-slate-400">
                              {formatComposeFileSize(
                                file.size
                              )}
                            </p>

                          </div>


                          <button
                            type="button"
                            disabled={
                              replying
                            }
                            onClick={() =>
                              removeReplyFile(
                                index
                              )
                            }
                            className="shrink-0 rounded-lg px-2 py-1 text-[10px] font-semibold text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                          >
                            Remove
                          </button>

                        </div>

                      )
                    )}

                  </div>

                )}

              </div>

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
