import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Inbox,
  Link2,
  Mail,
  RefreshCw,
  Settings as SettingsIcon,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import {
  useNavigate,
} from "react-router-dom";

import axios, {
  invalidateSession,
  refreshSessionAccessToken,
} from "../axiosConfig";

import {
  isJwtTokenFailurePayload,
} from "../authSession";

import {
  API_BASE_URL,
} from "../runtimeConfig";


const EMPTY_SUMMARY = {
  supported: 2,
  connected: 0,
  disconnected: 2,
  attention_required: 0,
  synced_once: 0,
};


const STATUS_META = {
  connected: {
    label: "Connected",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
    icon: CheckCircle2,
  },

  disconnected: {
    label: "Not connected",
    badge:
      "border-slate-200 bg-slate-50 text-slate-600",
    icon: Link2,
  },

  reauth_required: {
    label: "Reconnect required",
    badge:
      "border-amber-200 bg-amber-50 text-amber-700",
    icon: AlertTriangle,
  },

  admin_disabled: {
    label: "Disabled by administrator",
    badge:
      "border-rose-200 bg-rose-50 text-rose-700",
    icon: XCircle,
  },
};


const SYNC_META = {
  success: {
    label: "Sync healthy",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
  },

  syncing: {
    label: "Syncing",
    badge:
      "border-sky-200 bg-sky-50 text-sky-700",
  },

  failed: {
    label: "Sync failed",
    badge:
      "border-rose-200 bg-rose-50 text-rose-700",
  },

  idle: {
    label: "Idle",
    badge:
      "border-slate-200 bg-slate-50 text-slate-600",
  },

  not_started: {
    label: "Not synced yet",
    badge:
      "border-slate-200 bg-slate-50 text-slate-600",
  },
};


function wait(milliseconds) {
  return new Promise(
    (resolve) => {
      window.setTimeout(
        resolve,
        milliseconds
      );
    }
  );
}


function formatDate(value) {
  if (!value) {
    return "Never";
  }

  const parsed =
    new Date(value);

  if (
    Number.isNaN(
      parsed.getTime()
    )
  ) {
    return String(value);
  }

  return parsed.toLocaleString();
}


function SummaryCard({
  label,
  value,
  description,
  tone = "slate",
}) {
  const toneClass = {
    slate:
      "border-slate-200 bg-white",

    emerald:
      "border-emerald-200 bg-gradient-to-br from-white to-emerald-50",

    amber:
      "border-amber-200 bg-gradient-to-br from-white to-amber-50",

    sky:
      "border-sky-200 bg-gradient-to-br from-white to-sky-50",
  }[tone];

  return (
    <div
      className={`
        rounded-2xl border p-5 shadow-sm
        ${toneClass}
      `}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        {label}
      </p>

      <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>

      <p className="mt-2 text-xs leading-5 text-slate-500">
        {description}
      </p>
    </div>
  );
}


function Badge({
  children,
  className,
}) {
  return (
    <span
      className={`
        inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold
        ${className}
      `}
    >
      {children}
    </span>
  );
}


function MetaField({
  label,
  value,
}) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
        {label}
      </p>

      <p className="mt-1 break-words text-sm font-medium text-slate-700">
        {value || "Not available"}
      </p>
    </div>
  );
}


function ProviderIdentity({
  provider,
}) {
  const google =
    provider.provider ===
    "google";

  return (
    <div
      className={`
        flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-lg font-bold
        ${
          google
            ? "border border-rose-200 bg-rose-50 text-rose-700"
            : "border border-sky-200 bg-sky-50 text-sky-700"
        }
      `}
    >
      {google ? "G" : "M"}
    </div>
  );
}


export default function Settings() {
  const navigate =
    useNavigate();

  const [loading, setLoading] =
    useState(true);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [error, setError] =
    useState("");

  const [notice, setNotice] =
    useState("");

  const [providers, setProviders] =
    useState([]);

  const [summary, setSummary] =
    useState(EMPTY_SUMMARY);

  const [
    activeAction,
    setActiveAction,
  ] = useState("");

  const [
    signatureDrafts,
    setSignatureDrafts,
  ] = useState({});


  const applyPayload =
    useCallback(
      (payload) => {
        setProviders(
          Array.isArray(
            payload?.providers
          )
            ? payload.providers
            : []
        );

        setSummary({
          ...EMPTY_SUMMARY,
          ...(payload?.summary || {}),
        });
      },
      []
    );


  const loadStatus =
    useCallback(
      async ({
        background = false,
      } = {}) => {
        try {
          setError("");

          if (background) {
            setRefreshing(true);
          } else {
            setLoading(true);
          }

          const response =
            await axios.get(
              "/api/mail-adoption/"
            );

          applyPayload(
            response.data || {}
          );

          return (
            response.data || {}
          );
        } catch (err) {
          console.error(
            "Mail adoption load error:",
            err
          );

          if (
            err.response?.status ===
            403
          ) {
            setError(
              "An active organization membership is required to manage connected mailboxes."
            );
          } else {
            setError(
              "Unable to load mailbox connection status."
            );
          }

          return null;
        } finally {
          setLoading(false);

          if (background) {
            setRefreshing(false);
          }
        }
      },
      [
        applyPayload,
      ]
    );


  useEffect(() => {
    loadStatus();
  }, [loadStatus]);


  useEffect(
    () => {

      setSignatureDrafts(
        (current) => {

          const next = {
            ...current,
          };


          for (
            const provider
            of providers
          ) {

            if (
              !provider.account_id
            ) {
              continue;
            }


            const key =
              String(
                provider.account_id
              );


            if (
              Object.prototype
                .hasOwnProperty
                .call(
                  current,
                  key
                )
            ) {
              continue;
            }


            next[
              key
            ] = {
              enabled:
                Boolean(
                  provider
                    .signature_enabled
                ),

              text:
                provider
                  .signature_text ||
                "",
            };

          }


          return next;

        }
      );

    },
    [
      providers,
    ]
  );


  const connectMailbox =
    async (
      provider
    ) => {
      if (
        provider.connection_status ===
        "admin_disabled"
      ) {
        setError(
          `${provider.label} access is disabled by an administrator.`
        );

        return;
      }

      setError("");
      setNotice("");

      const actionKey =
        `connect:${provider.provider}`;

      setActiveAction(
        actionKey
      );

      /*
       * Open synchronously from the click event so browser
       * popup blockers do not reject the OAuth window after
       * the asynchronous start-API request.
       */
      const popup =
        window.open(
          "",
          `oneuch-oauth-${provider.provider}`,
          "width=620,height=760,resizable=yes,scrollbars=yes"
        );

      if (!popup) {
        setActiveAction("");

        setError(
          "The authorization window was blocked by the browser. Allow popups for One UCH and try again."
        );

        return;
      }

      try {
        popup.document.title =
          `Connect ${provider.label}`;

        popup.document.body.innerHTML =
          `
            <div style="
              font-family: Arial, sans-serif;
              padding: 32px;
              color: #0f172a;
            ">
              <h2 style="margin-bottom: 8px;">
                One UCH
              </h2>
              <p>
                Preparing secure authorization...
              </p>
            </div>
          `;

        const start =
          await axios.get(
            provider.connect_path
          );

        const authorizationUrl =
          start.data
            ?.authorization_url;

        if (!authorizationUrl) {
          throw new Error(
            "Authorization URL was not returned."
          );
        }

        popup.location.href =
          authorizationUrl;

        const deadline =
          Date.now() +
          120000;

        let connected =
          false;

        while (
          Date.now() <
          deadline
        ) {
          await wait(
            1500
          );

          const latest =
            await axios.get(
              "/api/mail-adoption/"
            );

          const payload =
            latest.data || {};

          applyPayload(
            payload
          );

          const current =
            (
              payload.providers ||
              []
            ).find(
              (item) =>
                item.provider ===
                provider.provider
            );

          if (
            current
              ?.connection_status ===
            "connected"
          ) {
            connected = true;
            break;
          }

          if (
            current
              ?.connection_status ===
            "admin_disabled"
          ) {
            break;
          }

          if (popup.closed) {
            break;
          }
        }

        if (connected) {
          if (!popup.closed) {
            popup.close();
          }

          setNotice(
            `${provider.label} is connected to One UCH.`
          );
        } else if (
          !popup.closed
        ) {
          setNotice(
            "Authorization has not completed yet. Finish the provider sign-in, then refresh mailbox status."
          );
        } else {
          setNotice(
            "Authorization window closed. Refresh mailbox status after completing provider authorization."
          );
        }

        await loadStatus({
          background: true,
        });
      } catch (err) {
        console.error(
          "Mailbox connection error:",
          err
        );

        if (!popup.closed) {
          popup.close();
        }

        setError(
          err.response?.data
            ?.detail ||
          err.response?.data
            ?.error ||
          err.message ||
          `Unable to start ${provider.label} authorization.`
        );
      } finally {
        setActiveAction("");
      }
    };


  const syncMailbox =
    async (
      provider
    ) => {
      setError("");
      setNotice("");

      const actionKey =
        `sync:${provider.provider}`;

      setActiveAction(
        actionKey
      );

      try {
        const accessToken =
          localStorage.getItem(
            "access"
          );

        if (!accessToken) {
          throw new Error(
            "Your One UCH session is unavailable. Please sign in again."
          );
        }

        const baseURL =
          API_BASE_URL;

        /*
         * Use the explicit fetch/JWT-refresh path for mailbox
         * synchronization requests.
         *
         * The endpoint now queues a governed Celery mailbox
         * task instead of holding this HTTP request open while
         * a 90-day provider history import runs.
         */
        const performSyncRequest =
          async (token) => {

            const response =
              await fetch(
                `${baseURL}${provider.sync_path}`,
                {
                  method: "POST",
                  headers: {
                    Authorization:
                      `Bearer ${token}`,
                    "Content-Type":
                      "application/json",
                  },
                }
              );


            let payload = {};


            try {

              payload =
                await response.json();

            } catch {

              payload = {};

            }


            return {
              response,
              payload,
            };

          };


        let {
          response,
          payload,
        } =
          await performSyncRequest(
            accessToken
          );


        /*
         * Distinguish an expired One UCH access token from the
         * provider's own "reauthenticate mailbox" HTTP 401.
         */
        if (
          response.status === 401
          && isJwtTokenFailurePayload(
            payload
          )
        ) {

          let refreshedAccessToken;


          try {

            refreshedAccessToken =
              await refreshSessionAccessToken();

          } catch (refreshError) {

            invalidateSession();

            throw refreshError;

          }


          ({
            response,
            payload,
          } =
            await performSyncRequest(
              refreshedAccessToken
            ));

        }


        if (!response.ok) {
          throw new Error(
            payload.action ||
            payload.message ||
            payload.error ||
            `Mailbox sync failed with status ${response.status}.`
          );
        }

        if (
          response.status === 202 ||
          payload.status ===
            "sync_queued"
        ) {
          setNotice(
            `${provider.label} synchronization started. You can continue using One UCH while the mailbox is processed in the background.`
          );
        } else {
          setNotice(
            `${provider.label} synchronization request completed.`
          );
        }

        await loadStatus({
          background: true,
        });
      } catch (err) {
        console.error(
          "Mailbox sync error:",
          err
        );

        setError(
          err.message ||
          `Unable to synchronize ${provider.label}.`
        );

        await loadStatus({
          background: true,
        });
      } finally {
        setActiveAction("");
      }
    };


  const saveMailboxSignature =
    async (
      provider
    ) => {

      if (
        !provider.account_id
      ) {
        return;
      }


      const key =
        String(
          provider.account_id
        );


      const draft =
        signatureDrafts[
          key
        ] || {
          enabled:
            Boolean(
              provider
                .signature_enabled
            ),

          text:
            provider
              .signature_text ||
            "",
        };


      const actionKey =
        `signature:${provider.account_id}`;


      try {

        setError("");
        setNotice("");

        setActiveAction(
          actionKey
        );


        const response =
          await axios.patch(
            (
              "/api/email/"
              +
              "mailbox-signature/"
              +
              provider.account_id
              +
              "/"
            ),
            {
              signature_enabled:
                Boolean(
                  draft.enabled
                ),

              signature_text:
                draft.text || "",
            }
          );


        setSignatureDrafts(
          (current) => ({
            ...current,

            [key]: {
              enabled:
                Boolean(
                  response.data
                    ?.signature_enabled
                ),

              text:
                response.data
                  ?.signature_text ||
                "",
            },
          })
        );


        setNotice(
          `${provider.label} outgoing signature saved.`
        );


        await loadStatus({
          background:
            true,
        });

      } catch (err) {

        console.error(
          "Mailbox signature error:",
          err
        );


        setError(
          err.response?.data
            ?.detail ||
          "Unable to save the mailbox signature."
        );

      } finally {

        setActiveAction(
          ""
        );

      }

    };


  const refreshStatus =
    async () => {
      setNotice("");

      await loadStatus({
        background: true,
      });
    };


  return (
    <div className="min-h-full bg-slate-50/70">

      <div className="mx-auto max-w-[1450px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

        {/* ==================================================
            HERO
        ================================================== */}

        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 shadow-xl shadow-slate-200/60">

          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-sky-500/10 blur-3xl" />

          <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-violet-500/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">

              <div className="max-w-3xl">

                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">

                  <SettingsIcon
                    size={14}
                  />

                  Mail Adoption

                </div>


                <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
                  Connected Mailboxes
                </h1>


                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                  Connect the mailboxes that feed One UCH.
                  OAuth authorization, token lifecycle and provider
                  synchronization remain controlled by the existing
                  Gmail and Microsoft integration services.
                </p>


                <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-300">

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Gmail OAuth
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Microsoft 365 OAuth
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Incremental mailbox sync
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    No credentials exposed
                  </span>

                </div>

              </div>


              <button
                type="button"
                onClick={
                  refreshStatus
                }
                disabled={
                  refreshing
                }
                className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >

                <RefreshCw
                  size={16}
                  className={
                    refreshing
                      ? "animate-spin"
                      : ""
                  }
                />

                {refreshing
                  ? "Refreshing"
                  : "Refresh status"}

              </button>

            </div>
          </div>
        </section>


        {/* ==================================================
            SECURITY BOUNDARY
        ================================================== */}

        <section className="mt-4 rounded-2xl border border-sky-200 bg-sky-50/70 px-5 py-4">

          <div className="flex items-start gap-3">

            <ShieldCheck
              size={19}
              className="mt-0.5 shrink-0 text-sky-700"
            />

            <div>

              <p className="text-sm font-semibold text-sky-950">
                Provider authorization stays with Google and Microsoft
              </p>

              <p className="mt-1 text-xs leading-5 text-sky-800">
                One UCH starts the existing OAuth flow and reports
                connection health. This page never displays or asks
                you to paste OAuth access or refresh tokens.
              </p>

            </div>
          </div>
        </section>


        {/* ==================================================
            FEEDBACK
        ================================================== */}

        {error && (
          <div className="mt-5 flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-800">

            <AlertTriangle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <div>
              <p className="font-semibold">
                Mailbox attention required
              </p>

              <p className="mt-1 text-rose-700">
                {error}
              </p>
            </div>

          </div>
        )}


        {notice && (
          <div className="mt-5 flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3.5 text-sm text-emerald-800">

            <CheckCircle2
              size={18}
              className="mt-0.5 shrink-0"
            />

            <div>
              <p className="font-semibold">
                Mailbox status updated
              </p>

              <p className="mt-1 text-emerald-700">
                {notice}
              </p>
            </div>

          </div>
        )}


        {/* ==================================================
            SUMMARY
        ================================================== */}

        <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          <SummaryCard
            label="Supported Providers"
            value={
              summary.supported
            }
            description="Gmail and Microsoft 365 / Outlook are supported in the current MVP."
          />

          <SummaryCard
            label="Connected"
            value={
              summary.connected
            }
            description="Provider mailboxes currently available to the One UCH integration layer."
            tone="emerald"
          />

          <SummaryCard
            label="Needs Attention"
            value={
              summary.attention_required
            }
            description="Connections that require user reauthorization or administrator action."
            tone="amber"
          />

          <SummaryCard
            label="Synced Before"
            value={
              summary.synced_once
            }
            description="Provider mailboxes with at least one recorded successful synchronization."
            tone="sky"
          />

        </section>


        {/* ==================================================
            LOADING
        ================================================== */}

        {loading ? (

          <section className="mt-6 grid gap-5 xl:grid-cols-2">

            {[1, 2].map(
              (item) => (
                <div
                  key={item}
                  className="animate-pulse rounded-[26px] border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <div className="h-12 w-12 rounded-2xl bg-slate-200" />
                  <div className="mt-5 h-5 w-48 rounded bg-slate-200" />
                  <div className="mt-3 h-4 w-64 rounded bg-slate-100" />
                  <div className="mt-6 h-32 rounded-2xl bg-slate-100" />
                </div>
              )
            )}

          </section>

        ) : (

          /* ==================================================
              PROVIDERS
          ================================================== */

          <section className="mt-6 grid gap-5 xl:grid-cols-2">

            {providers.map(
              (provider) => {
                const status =
                  STATUS_META[
                    provider.connection_status
                  ] ||
                  STATUS_META.disconnected;

                const StatusIcon =
                  status.icon;

                const sync =
                  SYNC_META[
                    provider.sync_status
                  ] ||
                  SYNC_META.not_started;

                const connecting =
                  activeAction ===
                  `connect:${provider.provider}`;

                const syncing =
                  activeAction ===
                  `sync:${provider.provider}`;

                const busy =
                  Boolean(
                    activeAction
                  );

                const adminDisabled =
                  provider.connection_status ===
                  "admin_disabled";

                const connectLabel =
                  provider.connection_status ===
                  "disconnected"
                    ? `Connect ${provider.label}`
                    : `Reconnect ${provider.label}`;

                return (
                  <article
                    key={
                      provider.provider
                    }
                    className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm"
                  >

                    <div className="border-b border-slate-200 bg-gradient-to-r from-white to-slate-50 p-5 lg:p-6">

                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

                        <div className="flex min-w-0 items-start gap-4">

                          <ProviderIdentity
                            provider={
                              provider
                            }
                          />


                          <div className="min-w-0">

                            <div className="flex flex-wrap items-center gap-2">

                              <h2 className="text-xl font-semibold tracking-tight text-slate-950">
                                {provider.label}
                              </h2>


                              <Badge
                                className={
                                  status.badge
                                }
                              >
                                <StatusIcon
                                  size={12}
                                  className="mr-1.5"
                                />

                                {status.label}
                              </Badge>

                            </div>


                            <p className="mt-2 break-all text-sm text-slate-600">
                              {provider.email_address ||
                                "No mailbox connected"}
                            </p>

                          </div>

                        </div>


                        <Badge
                          className={
                            sync.badge
                          }
                        >
                          <Activity
                            size={12}
                            className="mr-1.5"
                          />

                          {sync.label}
                        </Badge>

                      </div>

                    </div>


                    <div className="p-5 lg:p-6">

                      <div className="grid gap-4 sm:grid-cols-2">

                        <MetaField
                          label="Connection"
                          value={
                            status.label
                          }
                        />

                        <MetaField
                          label="Last Successful Sync"
                          value={formatDate(
                            provider.last_synced_at
                          )}
                        />

                        <MetaField
                          label="OAuth Token"
                          value={
                            provider.oauth_present
                              ? (
                                  provider.oauth_active
                                    ? "Active"
                                    : "Inactive"
                                )
                              : "Not present"
                          }
                        />

                        <MetaField
                          label="Refresh Capability"
                          value={
                            provider.refresh_available
                              ? "Available"
                              : "Not available"
                          }
                        />

                      </div>


                      {provider.token_expired &&
                        provider.refresh_available &&
                        provider.connected && (
                          <div className="mt-5 flex items-start gap-3 rounded-xl border border-sky-200 bg-sky-50 px-3.5 py-3 text-xs leading-5 text-sky-800">

                            <Clock3
                              size={16}
                              className="mt-0.5 shrink-0"
                            />

                            <p>
                              The current access token has expired,
                              but a refresh token is available.
                              Existing provider services will refresh
                              access when needed.
                            </p>

                          </div>
                        )}


                      {provider.sync_error && (
                        <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-3 text-xs leading-5 text-rose-800">

                          <AlertTriangle
                            size={16}
                            className="mt-0.5 shrink-0"
                          />

                          <p className="break-words">
                            {provider.sync_error}
                          </p>

                        </div>
                      )}


                      {adminDisabled && (
                        <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-3 text-xs leading-5 text-rose-800">

                          <ShieldCheck
                            size={16}
                            className="mt-0.5 shrink-0"
                          />

                          <p>
                            OAuth access has been disabled by an
                            administrator. User reconnection cannot
                            override this policy.
                          </p>

                        </div>
                      )}


                      {provider.connected &&
                        provider.account_id && (

                        <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">

                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">

                            <div>

                              <p className="text-sm font-semibold text-slate-900">
                                One UCH outgoing signature
                              </p>

                              <p className="mt-1 max-w-xl text-xs leading-5 text-slate-500">
                                This signature is controlled by One UCH and is appended deterministically when mail is sent from this mailbox.
                              </p>

                            </div>


                            <label className="flex shrink-0 items-center gap-2 text-xs font-semibold text-slate-700">

                              <input
                                type="checkbox"
                                checked={
                                  Boolean(
                                    (
                                      signatureDrafts[
                                        String(
                                          provider.account_id
                                        )
                                      ]
                                      ?.enabled
                                    )
                                    ??
                                    provider.signature_enabled
                                  )
                                }
                                onChange={
                                  (event) => {

                                    const key =
                                      String(
                                        provider.account_id
                                      );


                                    setSignatureDrafts(
                                      (current) => ({
                                        ...current,

                                        [key]: {
                                          enabled:
                                            event.target.checked,

                                          text:
                                            current[
                                              key
                                            ]?.text
                                            ??
                                            provider.signature_text
                                            ??
                                            "",
                                        },
                                      })
                                    );

                                  }
                                }
                                className="h-4 w-4 rounded border-slate-300"
                              />

                              Use signature

                            </label>

                          </div>


                          <textarea
                            rows={5}
                            value={
                              signatureDrafts[
                                String(
                                  provider.account_id
                                )
                              ]?.text
                              ??
                              provider.signature_text
                              ??
                              ""
                            }
                            onChange={
                              (event) => {

                                const key =
                                  String(
                                    provider.account_id
                                  );


                                setSignatureDrafts(
                                  (current) => ({
                                    ...current,

                                    [key]: {
                                      enabled:
                                        current[
                                          key
                                        ]?.enabled
                                        ??
                                        Boolean(
                                          provider.signature_enabled
                                        ),

                                      text:
                                        event.target.value,
                                    },
                                  })
                                );

                              }
                            }
                            placeholder="Kind regards, Name, Company, Contact details"
                            className="mt-4 w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
                          />


                          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

                            <p className="text-[11px] leading-5 text-slate-500">
                              Applies to New, Reply, Reply All, Forward and Draft ? Send. Native Gmail/Outlook client signatures are not assumed by the API send path.
                            </p>


                            <button
                              type="button"
                              onClick={() =>
                                saveMailboxSignature(
                                  provider
                                )
                              }
                              disabled={
                                Boolean(
                                  activeAction
                                )
                              }
                              className="shrink-0 rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {
                                activeAction ===
                                `signature:${provider.account_id}`
                                  ? "Saving..."
                                  : "Save signature"
                              }
                            </button>

                          </div>

                        </div>

                      )}


                      <div className="mt-6 flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row">

                        {!adminDisabled && (
                          <button
                            type="button"
                            onClick={() =>
                              connectMailbox(
                                provider
                              )
                            }
                            disabled={
                              busy
                            }
                            className={`
                              inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50
                              ${
                                provider.connected
                                  ? "border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                                  : "bg-slate-950 text-white shadow-sm hover:bg-slate-800"
                              }
                            `}
                          >

                            {connecting ? (
                              <RefreshCw
                                size={15}
                                className="animate-spin"
                              />
                            ) : (
                              <ExternalLink
                                size={15}
                              />
                            )}

                            {connecting
                              ? "Waiting for authorization"
                              : connectLabel}

                          </button>
                        )}


                        {provider.connected && (
                          <button
                            type="button"
                            onClick={() =>
                              syncMailbox(
                                provider
                              )
                            }
                            disabled={
                              busy
                            }
                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
                          >

                            <RefreshCw
                              size={15}
                              className={
                                syncing
                                  ? "animate-spin"
                                  : ""
                              }
                            />

                            {syncing
                              ? "Synchronizing"
                              : "Sync mailbox"}

                          </button>
                        )}


                        {provider.connected && (
                          <button
                            type="button"
                            onClick={() =>
                              navigate(
                                "/inbox"
                              )
                            }
                            disabled={
                              busy
                            }
                            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 disabled:opacity-50"
                          >
                            <Inbox
                              size={15}
                            />
                            Open Inbox
                          </button>
                        )}

                      </div>

                    </div>
                  </article>
                );
              }
            )}

          </section>
        )}


        {/* ==================================================
            OPERATIONAL EXPLANATION
        ================================================== */}

        <section className="mt-6 rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm lg:p-6">

          <div className="flex items-start gap-3">

            <Mail
              size={19}
              className="mt-0.5 shrink-0 text-slate-500"
            />

            <div className="max-w-4xl">

              <p className="text-sm font-semibold text-slate-950">
                How connected mailboxes feed One UCH
              </p>

              <p className="mt-2 text-sm leading-6 text-slate-600">
                Once a provider mailbox is connected and synchronized,
                its messages flow into the Unified Inbox. Existing One UCH
                processing can then turn communication into actions,
                commitments, waits, decisions, relationship context and
                governed evidence.
              </p>

            </div>

          </div>
        </section>

      </div>
    </div>
  );
}
