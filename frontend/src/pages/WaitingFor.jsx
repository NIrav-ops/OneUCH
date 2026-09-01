import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Clock,
  FileCheck2,
  History,
  Hourglass,
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import {
  useNavigate,
} from "react-router-dom";

import axios from "../axiosConfig";


const EMPTY_SUMMARY = {
  total: 0,
  overdue: 0,
  due_today: 0,
  upcoming: 0,
  no_due: 0,
};


const DUE_META = {
  overdue: {
    label: "Overdue",
    description:
      "The expected external response is past its explicit deadline.",
    badge:
      "border-rose-200 bg-rose-50 text-rose-700",
    panel:
      "border-rose-200 bg-rose-50",
    dot:
      "bg-rose-500",
  },

  due_today: {
    label: "Due Today",
    description:
      "The response is expected before today's deadline closes.",
    badge:
      "border-amber-200 bg-amber-50 text-amber-800",
    panel:
      "border-amber-200 bg-amber-50",
    dot:
      "bg-amber-500",
  },

  upcoming: {
    label: "Upcoming",
    description:
      "The response remains within its current expected window.",
    badge:
      "border-sky-200 bg-sky-50 text-sky-700",
    panel:
      "border-sky-200 bg-sky-50",
    dot:
      "bg-sky-500",
  },

  no_due: {
    label: "No Due Date",
    description:
      "The obligation is active but no explicit response deadline exists.",
    badge:
      "border-slate-200 bg-slate-50 text-slate-600",
    panel:
      "border-slate-200 bg-white",
    dot:
      "bg-slate-400",
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


function SummaryCard({
  label,
  value,
  description,
  tone = "slate",
}) {
  const toneClass = {
    slate:
      "border-slate-200 bg-white",

    rose:
      "border-rose-200 bg-gradient-to-br from-white to-rose-50",

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


export default function WaitingFor() {
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
    dueFilter,
    setDueFilter,
  ] = useState("all");

  const [
    evidenceFilter,
    setEvidenceFilter,
  ] = useState("all");


  const loadWaitingFor =
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
              "/api/knowledge/waiting-for/"
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
            "Waiting For load error:",
            err
          );

          if (
            err.response?.status ===
            403
          ) {
            setError(
              "An active organization membership is required to view Waiting For."
            );
          } else {
            setError(
              "Unable to load Waiting For. Please refresh and try again."
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
    loadWaitingFor();
  }, [loadWaitingFor]);


  const filteredItems =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      return items.filter(
        (item) => {
          const matchesDue =
            dueFilter === "all" ||
            item.due_state ===
              dueFilter;

          const evidenceQuality =
            item.evidence
              ?.evidence_quality ||
            "none";

          const matchesEvidence =
            evidenceFilter === "all" ||
            evidenceQuality ===
              evidenceFilter;

          const searchable = [
            item.waiting_id,
            item.commitment_id,
            item.obligation,
            item.counterparty,
            item.owner_email,
            item.source_status,
            item.evidence
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
            matchesDue &&
            matchesEvidence &&
            matchesSearch
          );
        }
      );
    }, [
      items,
      search,
      dueFilter,
      evidenceFilter,
    ]);


  const activeFilterCount = [
    search.trim() !== "",
    dueFilter !== "all",
    evidenceFilter !== "all",
  ].filter(Boolean).length;


  const clearFilters = () => {
    setSearch("");
    setDueFilter("all");
    setEvidenceFilter("all");
  };


  const openEmail = (
    item
  ) => {
    if (!item.open_url) {
      return;
    }

    navigate(
      item.open_url
    );
  };


  return (
    <div className="min-h-full bg-slate-50/70">

      <div className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

        {/* ==================================================
            HEADER
        ================================================== */}

        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 shadow-xl shadow-slate-200/60">

          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-sky-500/10 blur-3xl" />

          <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">

              <div className="max-w-3xl">

                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">

                  <Hourglass
                    size={14}
                  />

                  External Response Queue

                </div>


                <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
                  Waiting For
                </h1>


                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                  The active external obligations and
                  responses your organization is still
                  waiting to receive, backed by the original
                  communication evidence.
                </p>


                <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-300">

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    External accountability
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Evidence backed
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Auto-resolved on response
                  </span>

                </div>

              </div>


              <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">

                {generatedAt && (
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5">

                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Queue generated
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
                    loadWaitingFor({
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
                    : "Refresh queue"}

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
                Waiting For unavailable
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
            label="Active Waits"
            value={summary.total}
            description="External responses and obligations still outstanding."
          />

          <SummaryCard
            label="Overdue"
            value={summary.overdue}
            description="Expected responses already beyond their explicit deadline."
            tone="rose"
          />

          <SummaryCard
            label="Due Today"
            value={summary.due_today}
            description="External responses expected before today closes."
            tone="amber"
          />

          <SummaryCard
            label="Upcoming"
            value={summary.upcoming}
            description="Outstanding responses still inside their expected window."
            tone="sky"
          />

        </section>


        {/* ==================================================
            QUEUE STATE
        ================================================== */}

        <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">

          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

            <div>

              <p className="text-sm font-semibold text-slate-900">
                Response coverage
              </p>

              <p className="mt-1 text-xs text-slate-500">
                Only active external waits are shown here.
                Received and ignored items remain in Commitments.
              </p>

            </div>


            <div className="flex flex-wrap gap-2">

              <span className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                Overdue {summary.overdue}
              </span>

              <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
                Due Today {summary.due_today}
              </span>

              <span className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 ring-1 ring-inset ring-sky-200">
                Upcoming {summary.upcoming}
              </span>

              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700">
                No Due Date {summary.no_due}
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
                  placeholder="Search counterparty, obligation or evidence..."
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
                    "overdue",
                    "due_today",
                    "upcoming",
                    "no_due",
                  ].map(
                    (value) => (
                      <FilterButton
                        key={value}
                        active={
                          dueFilter ===
                          value
                        }
                        onClick={() =>
                          setDueFilter(
                            value
                          )
                        }
                      >
                        {value === "all"
                          ? "All due states"
                          : DUE_META[
                              value
                            ]?.label}
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
                            ]?.label}
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
              WAITING QUEUE
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
                    ? "No active external responses are outstanding"
                    : "No waits match these filters"}

                </h2>


                <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">

                  {items.length === 0
                    ? "One UCH currently has no active ExpectedResponseItem obligations waiting on an external party."
                    : "Adjust or clear your filters to return to the complete active Waiting For queue."}

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
                    const due =
                      DUE_META[
                        item.due_state
                      ] ||
                      DUE_META.no_due;

                    const evidenceQuality =
                      item.evidence
                        ?.evidence_quality ||
                      "none";

                    const evidence =
                      EVIDENCE_META[
                        evidenceQuality
                      ] ||
                      EVIDENCE_META.none;

                    const evidenceText =
                      item.evidence
                        ?.evidence_text ||
                      "";

                    return (
                      <article
                        key={
                          item.waiting_id
                        }
                        className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm transition hover:border-slate-300 hover:shadow-md"
                      >

                        <div className="grid xl:grid-cols-[minmax(0,1fr)_380px]">

                          {/* ================================
                              PRIMARY
                          ================================ */}

                          <div className="p-5 lg:p-6">

                            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">

                              <div className="min-w-0">

                                <div className="flex flex-wrap items-center gap-2">

                                  <Badge
                                    className="border-emerald-200 bg-emerald-50 text-emerald-700"
                                  >
                                    <Hourglass
                                      size={12}
                                      className="mr-1.5"
                                    />

                                    Waiting
                                  </Badge>


                                  <Badge
                                    className={
                                      due.badge
                                    }
                                  >
                                    <span
                                      className={`
                                        mr-2 h-1.5 w-1.5 rounded-full
                                        ${due.dot}
                                      `}
                                    />

                                    {due.label}
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
                                    "External response expected"}
                                </h2>


                                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                                  One UCH is actively waiting
                                  for this external obligation
                                  to be fulfilled.
                                </p>

                              </div>


                              {item.open_url && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    openEmail(
                                      item
                                    )
                                  }
                                  className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-slate-950 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
                                >

                                  <Mail
                                    size={15}
                                  />

                                  Open Email

                                </button>
                              )}

                            </div>


                            {/* ================================
                                ACCOUNTABILITY
                            ================================ */}

                            <div className="mt-6 grid gap-4 rounded-2xl border border-slate-100 bg-slate-50/70 p-4 sm:grid-cols-2 lg:grid-cols-4">

                              <MetaField
                                label="Waiting On"
                                value={
                                  item.counterparty ||
                                  "External party not identified"
                                }
                              />

                              <MetaField
                                label="Internal Owner"
                                value={
                                  item.owner_email ||
                                  "Not available"
                                }
                              />

                              <MetaField
                                label="Current Deadline"
                                value={formatDate(
                                  item.current_due_at
                                )}
                              />

                              <MetaField
                                label="Tracking State"
                                value="Waiting"
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
                                  Response deadline history
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
                              EVIDENCE PANEL
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
                                The source communication is
                                linked, but an exact evidence
                                excerpt is not available.
                              </div>

                            )}


                            <div className="mt-5 border-t border-slate-200 pt-5">

                              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                                Accountability context
                              </p>


                              <div className="mt-4 space-y-3">

                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Waiting on
                                  </span>

                                  <span className="max-w-[220px] break-words text-right font-semibold text-slate-700">
                                    {item.counterparty ||
                                      "Unknown"}
                                  </span>

                                </div>


                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Source message
                                  </span>

                                  <span className="font-semibold text-slate-700">
                                    #{item.source_message_id}
                                  </span>

                                </div>


                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Waiting ID
                                  </span>

                                  <span className="max-w-[220px] truncate text-right font-semibold text-slate-700">
                                    {item.waiting_id}
                                  </span>

                                </div>

                              </div>
                            </div>


                            <div
                              className={`
                                mt-5 flex items-start gap-2 rounded-xl border px-3 py-3 text-xs font-medium
                                ${due.panel}
                              `}
                            >

                              {item.due_state ===
                              "overdue" ? (
                                <AlertTriangle
                                  size={14}
                                  className="mt-0.5 shrink-0"
                                />
                              ) : item.due_state ===
                                "due_today" ? (
                                <CalendarClock
                                  size={14}
                                  className="mt-0.5 shrink-0"
                                />
                              ) : item.due_state ===
                                "no_due" ? (
                                <UserRound
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
                                {due.description}
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
