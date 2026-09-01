import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  FileCheck2,
  Handshake,
  History,
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
  User,
} from "lucide-react";

import {
  useNavigate,
} from "react-router-dom";

import axios from "../axiosConfig";


const EMPTY_SUMMARY = {
  total: 0,
  pending: 0,
  fulfilled: 0,
  ignored: 0,
  cancelled: 0,
  we_owe_them: 0,
  they_owe_us: 0,
};


const DIRECTION_META = {
  WE_OWE_THEM: {
    label: "We owe them",
    description:
      "An external communication contains an obligation our organization must fulfill.",
    badge:
      "border-indigo-200 bg-indigo-50 text-indigo-700",
    panel:
      "border-indigo-200 bg-indigo-50/70",
  },

  THEY_OWE_US: {
    label: "They owe us",
    description:
      "An external party has an expected response or obligation back to us.",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
    panel:
      "border-emerald-200 bg-emerald-50/70",
  },
};


const STATUS_META = {
  pending: {
    label: "Pending",
    badge:
      "border-amber-200 bg-amber-50 text-amber-800",
    dot:
      "bg-amber-500",
  },

  fulfilled: {
    label: "Fulfilled",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
    dot:
      "bg-emerald-500",
  },

  ignored: {
    label: "Ignored",
    badge:
      "border-slate-200 bg-slate-50 text-slate-600",
    dot:
      "bg-slate-400",
  },

  cancelled: {
    label: "Cancelled",
    badge:
      "border-rose-200 bg-rose-50 text-rose-700",
    dot:
      "bg-rose-500",
  },
};


const EVIDENCE_META = {
  exact: {
    label: "Exact evidence",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
  },

  source_only: {
    label: "Source linked",
    badge:
      "border-sky-200 bg-sky-50 text-sky-700",
  },

  none: {
    label: "No exact evidence",
    badge:
      "border-slate-200 bg-slate-50 text-slate-600",
  },
};


const FULFILLMENT_META = {
  message_confirmed: {
    label: "Message confirmed",
    description:
      "A communication message confirms fulfillment.",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
  },

  manual_attestation: {
    label: "Manual attestation",
    description:
      "Completion was explicitly attested by a user.",
    badge:
      "border-blue-200 bg-blue-50 text-blue-700",
  },

  status_only: {
    label: "Status only",
    description:
      "A fulfilled lifecycle state exists without stronger evidence.",
    badge:
      "border-amber-200 bg-amber-50 text-amber-700",
  },

  none: {
    label: "No fulfillment record",
    description:
      "No fulfillment evidence is currently recorded.",
    badge:
      "border-slate-200 bg-white text-slate-600",
  },
};


function formatDate(value) {
  if (!value) {
    return "Not set";
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


function formatLabel(value) {
  if (!value) {
    return "";
  }

  return String(value)
    .toLowerCase()
    .split("_")
    .filter(Boolean)
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1)
    )
    .join(" ");
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

    amber:
      "border-amber-200 bg-gradient-to-br from-white to-amber-50",

    emerald:
      "border-emerald-200 bg-gradient-to-br from-white to-emerald-50",

    indigo:
      "border-indigo-200 bg-gradient-to-br from-white to-indigo-50",
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


function FilterButton({
  active,
  onClick,
  children,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        rounded-xl px-3.5 py-2 text-sm font-medium transition
        ${
          active
            ? "bg-slate-950 text-white shadow-sm"
            : "border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
        }
      `}
    >
      {children}
    </button>
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


export default function Commitments() {
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

  const [items, setItems] =
    useState([]);

  const [summary, setSummary] =
    useState(EMPTY_SUMMARY);

  const [
    generatedAt,
    setGeneratedAt,
  ] = useState(null);

  const [search, setSearch] =
    useState("");

  const [
    directionFilter,
    setDirectionFilter,
  ] = useState("all");

  const [
    statusFilter,
    setStatusFilter,
  ] = useState("all");

  const [
    evidenceFilter,
    setEvidenceFilter,
  ] = useState("all");

  const [
    fulfillmentFilter,
    setFulfillmentFilter,
  ] = useState("all");


  const loadCommitments =
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
              "/api/knowledge/commitments/"
            );

          const payload =
            response.data || {};

          setItems(
            Array.isArray(
              payload.items
            )
              ? payload.items
              : []
          );

          setSummary({
            ...EMPTY_SUMMARY,
            ...(payload.summary || {}),
          });

          setGeneratedAt(
            payload.generated_at ||
              null
          );
        } catch (err) {
          console.error(
            "Commitments load error:",
            err
          );

          if (
            err.response?.status ===
            403
          ) {
            setError(
              "An active organization membership is required to view Commitments."
            );
          } else {
            setError(
              "Unable to load Commitments. Please refresh and try again."
            );
          }
        } finally {
          setLoading(false);
          setRefreshing(false);
        }
      },
      []
    );


  useEffect(() => {
    loadCommitments();
  }, [loadCommitments]);


  const filteredItems =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      return items.filter(
        (item) => {
          const matchesDirection =
            directionFilter ===
              "all" ||
            item.direction ===
              directionFilter;

          const matchesStatus =
            statusFilter === "all" ||
            item.status ===
              statusFilter;

          const evidenceQuality =
            item.evidence
              ?.evidence_quality ||
            "none";

          const matchesEvidence =
            evidenceFilter === "all" ||
            evidenceQuality ===
              evidenceFilter;

          const fulfillmentMethod =
            item.fulfillment
              ?.method ||
            "none";

          const matchesFulfillment =
            fulfillmentFilter ===
              "all" ||
            fulfillmentMethod ===
              fulfillmentFilter;

          const searchable = [
            item.commitment_id,
            item.obligation,
            item.counterparty,
            item.owner_email,
            item.status,
            item.source_status,
            item.direction,
            item.source_object_type,
            item.evidence
              ?.evidence_text,
            item.fulfillment
              ?.evidence_text,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

          const matchesSearch =
            !query ||
            searchable.includes(
              query
            );

          return (
            matchesDirection &&
            matchesStatus &&
            matchesEvidence &&
            matchesFulfillment &&
            matchesSearch
          );
        }
      );
    }, [
      items,
      search,
      directionFilter,
      statusFilter,
      evidenceFilter,
      fulfillmentFilter,
    ]);


  const activeFilterCount = [
    search.trim() !== "",
    directionFilter !== "all",
    statusFilter !== "all",
    evidenceFilter !== "all",
    fulfillmentFilter !== "all",
  ].filter(Boolean).length;


  const clearFilters = () => {
    setSearch("");
    setDirectionFilter("all");
    setStatusFilter("all");
    setEvidenceFilter("all");
    setFulfillmentFilter("all");
  };


  const openConversation = (
    conversationId
  ) => {
    if (!conversationId) {
      return;
    }

    navigate(
      `/inbox?conversation=${encodeURIComponent(
        conversationId
      )}`
    );
  };


  const openExecution = (
    item
  ) => {
    if (
      item.source_object_type ===
      "action"
    ) {
      navigate("/actions");
      return;
    }

    if (item.conversation_id) {
      openConversation(
        item.conversation_id
      );
    }
  };


  return (
    <div className="min-h-full bg-slate-50/70">

      <div className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

        {/* ==================================================
            ENTERPRISE HEADER
        ================================================== */}

        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 shadow-xl shadow-slate-200/60">

          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-indigo-500/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">

              <div className="max-w-3xl">

                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">

                  <Handshake
                    size={14}
                  />

                  Accountability Ledger

                </div>


                <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
                  Commitments
                </h1>


                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                  A governed view of what we have committed
                  to others and what others have committed
                  back to us, with source evidence and
                  fulfillment provenance preserved.
                </p>


                <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-300">

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Evidence backed
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Bidirectional accountability
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Read-only ledger
                  </span>

                </div>
              </div>


              <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">

                {generatedAt && (
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5">

                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Ledger generated
                    </p>

                    <p className="mt-1 text-xs font-medium text-slate-200">
                      {formatDate(
                        generatedAt
                      )}
                    </p>

                  </div>
                )}


                <button
                  type="button"
                  onClick={() =>
                    loadCommitments({
                      background: true,
                    })
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
                    : "Refresh ledger"}

                </button>
              </div>
            </div>
          </div>
        </section>


        {/* ==================================================
            ERROR
        ================================================== */}

        {error && (
          <div className="mt-5 flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-800">

            <AlertTriangle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <div>

              <p className="font-semibold">
                Commitment ledger unavailable
              </p>

              <p className="mt-1 text-rose-700">
                {error}
              </p>

            </div>
          </div>
        )}


        {/* ==================================================
            SUMMARY
        ================================================== */}

        <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          <SummaryCard
            label="Total Commitments"
            value={summary.total}
            description="Communication-backed obligations in the organization ledger."
          />

          <SummaryCard
            label="Pending"
            value={summary.pending}
            description="Commitments whose authoritative lifecycle remains pending."
            tone="amber"
          />

          <SummaryCard
            label="Fulfilled"
            value={summary.fulfilled}
            description="Commitments with a fulfilled business-state projection."
            tone="emerald"
          />

          <SummaryCard
            label="They Owe Us"
            value={summary.they_owe_us}
            description="Responses or obligations currently attributed to external parties."
            tone="indigo"
          />

        </section>


        {/* ==================================================
            DIRECTION / STATUS STRIP
        ================================================== */}

        <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">

          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

            <div>

              <p className="text-sm font-semibold text-slate-900">
                Accountability balance
              </p>

              <p className="mt-1 text-xs text-slate-500">
                Server-derived commitment direction and lifecycle state.
              </p>

            </div>


            <div className="flex flex-wrap gap-2">

              <span className="rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200">
                We Owe Them {summary.we_owe_them}
              </span>

              <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
                They Owe Us {summary.they_owe_us}
              </span>

              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700">
                Ignored {summary.ignored}
              </span>

              <span className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                Cancelled {summary.cancelled}
              </span>

            </div>
          </div>
        </section>


        {/* ==================================================
            FILTERS
        ================================================== */}

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:p-5">

          <div className="flex flex-col gap-4">

            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">

              <div className="relative w-full lg:max-w-xl">

                <Search
                  size={17}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                />

                <input
                  value={search}
                  onChange={
                    (event) =>
                      setSearch(
                        event.target.value
                      )
                  }
                  placeholder="Search obligation, counterparty, owner or evidence..."
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:bg-white"
                />

              </div>


              <div className="flex items-center gap-3">

                <p className="text-xs font-medium text-slate-500">
                  Showing{" "}
                  <span className="font-semibold text-slate-900">
                    {filteredItems.length}
                  </span>{" "}
                  of{" "}
                  <span className="font-semibold text-slate-900">
                    {items.length}
                  </span>
                </p>

                {activeFilterCount > 0 && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="text-xs font-semibold text-slate-600 underline-offset-4 hover:text-slate-950 hover:underline"
                  >
                    Clear filters
                  </button>
                )}

              </div>
            </div>


            <div className="border-t border-slate-100 pt-4">

              <div className="flex flex-col gap-3">

                <div className="flex flex-wrap gap-2">

                  {[
                    "all",
                    "WE_OWE_THEM",
                    "THEY_OWE_US",
                  ].map(
                    (value) => (
                      <FilterButton
                        key={value}
                        active={
                          directionFilter ===
                          value
                        }
                        onClick={() =>
                          setDirectionFilter(
                            value
                          )
                        }
                      >
                        {value === "all"
                          ? "All directions"
                          : value ===
                            "WE_OWE_THEM"
                          ? "We owe them"
                          : "They owe us"}
                      </FilterButton>
                    )
                  )}

                </div>


                <div className="flex flex-wrap gap-2">

                  {[
                    "all",
                    "pending",
                    "fulfilled",
                    "ignored",
                    "cancelled",
                  ].map(
                    (value) => (
                      <FilterButton
                        key={value}
                        active={
                          statusFilter ===
                          value
                        }
                        onClick={() =>
                          setStatusFilter(
                            value
                          )
                        }
                      >
                        {value === "all"
                          ? "All statuses"
                          : formatLabel(
                              value
                            )}
                      </FilterButton>
                    )
                  )}

                </div>


                <div className="flex flex-wrap gap-2">

                  {[
                    "all",
                    "exact",
                    "source_only",
                    "none",
                  ].map(
                    (value) => (
                      <FilterButton
                        key={value}
                        active={
                          evidenceFilter ===
                          value
                        }
                        onClick={() =>
                          setEvidenceFilter(
                            value
                          )
                        }
                      >
                        {value === "all"
                          ? "All evidence"
                          : EVIDENCE_META[
                              value
                            ]?.label ||
                            formatLabel(
                              value
                            )}
                      </FilterButton>
                    )
                  )}

                </div>


                <div className="flex flex-wrap gap-2">

                  {[
                    "all",
                    "message_confirmed",
                    "manual_attestation",
                    "status_only",
                    "none",
                  ].map(
                    (value) => (
                      <FilterButton
                        key={value}
                        active={
                          fulfillmentFilter ===
                          value
                        }
                        onClick={() =>
                          setFulfillmentFilter(
                            value
                          )
                        }
                      >
                        {value === "all"
                          ? "All fulfillment"
                          : FULFILLMENT_META[
                              value
                            ]?.label ||
                            formatLabel(
                              value
                            )}
                      </FilterButton>
                    )
                  )}

                </div>

              </div>
            </div>
          </div>
        </section>


        {/* ==================================================
            LOADING
        ================================================== */}

        {loading ? (
          <div className="mt-6 space-y-4">

            {[1, 2, 3].map(
              (value) => (
                <div
                  key={value}
                  className="animate-pulse rounded-[24px] border border-slate-200 bg-white p-6 shadow-sm"
                >

                  <div className="h-4 w-32 rounded bg-slate-200" />

                  <div className="mt-5 h-6 w-2/3 rounded bg-slate-200" />

                  <div className="mt-3 h-4 w-full rounded bg-slate-100" />

                  <div className="mt-2 h-4 w-4/5 rounded bg-slate-100" />

                </div>
              )
            )}

          </div>
        ) : (

          /* ==================================================
              LEDGER
          ================================================== */

          <section className="mt-6">

            {filteredItems.length === 0 ? (

              <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">

                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">

                  <CheckCircle2
                    size={24}
                  />

                </div>


                <h2 className="mt-4 text-lg font-semibold text-slate-900">

                  {items.length === 0
                    ? "No communication-backed commitments found"
                    : "No commitments match these filters"}

                </h2>


                <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">

                  {items.length === 0
                    ? "One UCH currently has no governed commitment ledger entries for this organization."
                    : "Adjust or clear your filters to return to the complete commitment ledger."}

                </p>


                {items.length > 0 && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="mt-5 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
                  >
                    Clear filters
                  </button>
                )}

              </div>

            ) : (

              <div className="space-y-4">

                {filteredItems.map(
                  (item) => {
                    const direction =
                      DIRECTION_META[
                        item.direction
                      ] || {
                        label:
                          formatLabel(
                            item.direction
                          ),
                        description: "",
                        badge:
                          "border-slate-200 bg-slate-50 text-slate-700",
                        panel:
                          "border-slate-200 bg-slate-50",
                      };

                    const status =
                      STATUS_META[
                        item.status
                      ] ||
                      STATUS_META.pending;

                    const evidenceQuality =
                      item.evidence
                        ?.evidence_quality ||
                      "none";

                    const evidence =
                      EVIDENCE_META[
                        evidenceQuality
                      ] ||
                      EVIDENCE_META.none;

                    const fulfillmentMethod =
                      item.fulfillment
                        ?.method ||
                      "none";

                    const fulfillment =
                      FULFILLMENT_META[
                        fulfillmentMethod
                      ] ||
                      FULFILLMENT_META.none;

                    const evidenceText =
                      item.evidence
                        ?.evidence_text ||
                      "";

                    const fulfillmentText =
                      item.fulfillment
                        ?.evidence_text ||
                      "";

                    const hasSource =
                      Boolean(
                        item.conversation_id ||
                        item.source_message_id
                      );

                    return (
                      <article
                        key={
                          item.commitment_id
                        }
                        className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm transition hover:border-slate-300 hover:shadow-md"
                      >

                        <div className="grid xl:grid-cols-[minmax(0,1fr)_390px]">

                          {/* ================================
                              PRIMARY LEDGER ENTRY
                          ================================ */}

                          <div className="p-5 lg:p-6">

                            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">

                              <div className="min-w-0">

                                <div className="flex flex-wrap items-center gap-2">

                                  <Badge
                                    className={
                                      direction.badge
                                    }
                                  >
                                    {direction.label}
                                  </Badge>


                                  <Badge
                                    className={
                                      status.badge
                                    }
                                  >
                                    <span
                                      className={`
                                        mr-2 h-1.5 w-1.5 rounded-full
                                        ${status.dot}
                                      `}
                                    />

                                    {status.label}
                                  </Badge>


                                  <Badge
                                    className={
                                      evidence.badge
                                    }
                                  >
                                    <FileCheck2
                                      size={12}
                                      className="mr-1.5"
                                    />

                                    {evidence.label}
                                  </Badge>

                                </div>


                                <h2 className="mt-4 text-xl font-semibold tracking-tight text-slate-950">
                                  {item.obligation ||
                                    "Communication commitment"}
                                </h2>


                                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                                  {direction.description}
                                </p>

                              </div>


                              <div className="flex shrink-0 flex-wrap gap-2">

                                {item.conversation_id && (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      openConversation(
                                        item.conversation_id
                                      )
                                    }
                                    className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
                                  >
                                    <Mail
                                      size={15}
                                    />

                                    Open Email
                                  </button>
                                )}


                                {item.source_object_type ===
                                  "action" && (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      openExecution(
                                        item
                                      )
                                    }
                                    className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
                                  >
                                    Open Action

                                    <ArrowUpRight
                                      size={15}
                                    />
                                  </button>
                                )}

                              </div>
                            </div>


                            {/* ================================
                                ACCOUNTABILITY METADATA
                            ================================ */}

                            <div className="mt-6 grid gap-4 rounded-2xl border border-slate-100 bg-slate-50/70 p-4 sm:grid-cols-2 lg:grid-cols-4">

                              <MetaField
                                label="Counterparty"
                                value={
                                  item.counterparty ||
                                  "Not identified"
                                }
                              />

                              <MetaField
                                label="Internal Owner"
                                value={
                                  item.owner_email ||
                                  "Unassigned"
                                }
                              />

                              <MetaField
                                label="Current Deadline"
                                value={formatDate(
                                  item.current_due_at
                                )}
                              />

                              <MetaField
                                label="Source Status"
                                value={formatLabel(
                                  item.source_status
                                )}
                              />

                            </div>


                            {/* ================================
                                DEADLINE HISTORY
                            ================================ */}

                            <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-4">

                              <div className="flex items-center gap-2">

                                <History
                                  size={16}
                                  className="text-slate-400"
                                />

                                <p className="text-sm font-semibold text-slate-900">
                                  Deadline history
                                </p>

                              </div>


                              <div className="mt-4 grid gap-4 sm:grid-cols-3">

                                <MetaField
                                  label="Original"
                                  value={formatDate(
                                    item.original_due_at
                                  )}
                                />

                                <MetaField
                                  label="Current"
                                  value={formatDate(
                                    item.current_due_at
                                  )}
                                />

                                <MetaField
                                  label="Changes"
                                  value={String(
                                    item.deadline_change_count ??
                                    0
                                  )}
                                />

                              </div>
                            </div>

                          </div>


                          {/* ================================
                              EVIDENCE / FULFILLMENT
                          ================================ */}

                          <aside className="border-t border-slate-200 bg-slate-50/70 p-5 xl:border-l xl:border-t-0 xl:p-6">

                            <div className="flex items-center justify-between gap-3">

                              <div>

                                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                                  Source evidence
                                </p>

                                <p className="mt-1 text-xs font-medium text-slate-600">
                                  {evidence.label}
                                </p>

                              </div>


                              <ShieldCheck
                                size={18}
                                className="text-slate-400"
                              />

                            </div>


                            {evidenceText ? (

                              <blockquote className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-700 shadow-sm">
                                "{evidenceText}"
                              </blockquote>

                            ) : (

                              <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-500">

                                {hasSource
                                  ? "Source communication is linked, but an exact excerpt is not available."
                                  : "No source evidence excerpt is available for this ledger entry."}

                              </div>

                            )}


                            <div className="mt-5 border-t border-slate-200 pt-5">

                              <div className="flex items-center justify-between gap-3">

                                <div>

                                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                                    Fulfillment provenance
                                  </p>

                                  <p className="mt-1 text-xs text-slate-500">
                                    Evidence supporting the fulfillment state.
                                  </p>

                                </div>


                                <CheckCircle2
                                  size={18}
                                  className="text-slate-400"
                                />

                              </div>


                              <div className="mt-3">

                                <Badge
                                  className={
                                    fulfillment.badge
                                  }
                                >
                                  {fulfillment.label}
                                </Badge>

                              </div>


                              <p className="mt-3 text-xs leading-5 text-slate-600">
                                {fulfillment.description}
                              </p>


                              {fulfillmentText && (
                                <div className="mt-3 rounded-xl border border-slate-200 bg-white p-3 text-xs leading-5 text-slate-700">
                                  "{fulfillmentText}"
                                </div>
                              )}


                              <div className="mt-4 space-y-3">

                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Fulfilled at
                                  </span>

                                  <span className="text-right font-semibold text-slate-700">
                                    {formatDate(
                                      item.fulfillment
                                        ?.fulfilled_at
                                    )}
                                  </span>

                                </div>


                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Fulfillment quality
                                  </span>

                                  <span className="text-right font-semibold text-slate-700">
                                    {formatLabel(
                                      item.fulfillment
                                        ?.quality ||
                                      "none"
                                    )}
                                  </span>

                                </div>


                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Commitment ID
                                  </span>

                                  <span className="max-w-[220px] truncate text-right font-semibold text-slate-700">
                                    {item.commitment_id}
                                  </span>

                                </div>

                              </div>
                            </div>


                            <div
                              className={`
                                mt-5 flex items-start gap-2 rounded-xl border px-3 py-3 text-xs font-medium
                                ${direction.panel}
                              `}
                            >

                              {item.direction ===
                              "WE_OWE_THEM" ? (
                                <User
                                  size={14}
                                  className="mt-0.5 shrink-0"
                                />
                              ) : (
                                <Clock
                                  size={14}
                                  className="mt-0.5 shrink-0"
                                />
                              )}


                              <span>
                                {direction.label}
                              </span>

                            </div>

                          </aside>
                        </div>
                      </article>
                    );
                  }
                )}

              </div>
            )}

          </section>
        )}

      </div>
    </div>
  );
}
