import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  Mail,
  RefreshCw,
  Scale,
  Search,
  ShieldCheck,
  UserRound,
  XCircle,
} from "lucide-react";

import {
  useNavigate,
} from "react-router-dom";

import axios from "../axiosConfig";


const EMPTY_SUMMARY = {
  total: 0,
  approved: 0,
  rejected: 0,
  with_notes: 0,
  exact_request_evidence: 0,
};


const OUTCOME_META = {
  approved: {
    label: "Approved",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
    panel:
      "border-emerald-200 bg-emerald-50/70",
    icon: CheckCircle2,
  },

  rejected: {
    label: "Rejected",
    badge:
      "border-rose-200 bg-rose-50 text-rose-700",
    panel:
      "border-rose-200 bg-rose-50/70",
    icon: XCircle,
  },
};


const EVIDENCE_META = {
  exact: {
    label: "Exact request evidence",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
  },

  source_only: {
    label: "Source linked",
    badge:
      "border-sky-200 bg-sky-50 text-sky-700",
  },

  none: {
    label: "No request evidence",
    badge:
      "border-slate-200 bg-slate-50 text-slate-600",
  },
};


function formatDate(value) {
  if (!value) {
    return "Not recorded";
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

    emerald:
      "border-emerald-200 bg-gradient-to-br from-white to-emerald-50",

    rose:
      "border-rose-200 bg-gradient-to-br from-white to-rose-50",

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
        {value || "Not recorded"}
      </p>
    </div>
  );
}


export default function Decisions() {
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

  const [search, setSearch] =
    useState("");

  const [
    outcomeFilter,
    setOutcomeFilter,
  ] = useState("all");

  const [
    evidenceFilter,
    setEvidenceFilter,
  ] = useState("all");

  const [
    notesFilter,
    setNotesFilter,
  ] = useState("all");


  const loadDecisions =
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
              "/api/knowledge/decisions/"
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
        } catch (err) {
          console.error(
            "Decisions load error:",
            err
          );

          if (
            err.response?.status ===
            403
          ) {
            setError(
              "An active organization membership is required to view Decisions."
            );
          } else {
            setError(
              "Unable to load Decisions. Please refresh and try again."
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
    loadDecisions();
  }, [loadDecisions]);


  const filteredItems =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      return items.filter(
        (item) => {
          const matchesOutcome =
            outcomeFilter === "all" ||
            item.outcome ===
              outcomeFilter;

          const evidenceQuality =
            item.request_evidence
              ?.evidence_quality ||
            "none";

          const matchesEvidence =
            evidenceFilter === "all" ||
            evidenceQuality ===
              evidenceFilter;

          const hasNotes =
            Boolean(
              item.decision_notes
                ?.trim()
            );

          const matchesNotes =
            notesFilter === "all" ||
            (
              notesFilter ===
                "with_notes" &&
              hasNotes
            ) ||
            (
              notesFilter ===
                "without_notes" &&
              !hasNotes
            );

          const searchable = [
            item.decision_id,
            item.title,
            item.description,
            item.outcome,
            item.decision_notes,
            item.decision_by_email,
            item.requested_by,
            item.assigned_to_email,
            item.source_type,
            item.request_evidence
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
            matchesOutcome &&
            matchesEvidence &&
            matchesNotes &&
            matchesSearch
          );
        }
      );
    }, [
      items,
      search,
      outcomeFilter,
      evidenceFilter,
      notesFilter,
    ]);


  const activeFilterCount = [
    search.trim() !== "",
    outcomeFilter !== "all",
    evidenceFilter !== "all",
    notesFilter !== "all",
  ].filter(Boolean).length;


  const clearFilters = () => {
    setSearch("");
    setOutcomeFilter("all");
    setEvidenceFilter("all");
    setNotesFilter("all");
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

          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl" />

          <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">

              <div className="max-w-3xl">

                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">

                  <Scale
                    size={14}
                  />

                  Decision Register

                </div>


                <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
                  Decisions
                </h1>


                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                  A governed register of final approvals
                  and rejections, showing what was decided,
                  who recorded the decision, when it happened,
                  and the original request context behind it.
                </p>


                <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-300">

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Final outcomes only
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Decision provenance
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Request evidence separated
                  </span>

                </div>

              </div>


              <button
                type="button"
                onClick={() =>
                  loadDecisions({
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
                  : "Refresh register"}

              </button>

            </div>
          </div>
        </section>


        {/* ==================================================
            TRUTH BOUNDARY
        ================================================== */}

        <section className="mt-4 rounded-2xl border border-indigo-200 bg-indigo-50/70 px-5 py-4">

          <div className="flex items-start gap-3">

            <ShieldCheck
              size={19}
              className="mt-0.5 shrink-0 text-indigo-700"
            />

            <div>

              <p className="text-sm font-semibold text-indigo-950">
                Decision record and request evidence are different things
              </p>

              <p className="mt-1 text-xs leading-5 text-indigo-800">
                Outcome, decision actor, timestamp and notes
                represent the recorded decision. The source
                communication proves what approval was requested,
                not the decision itself.
              </p>

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
                Decision register unavailable
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
            label="Recorded Decisions"
            value={summary.total}
            description="Final approved and rejected approval outcomes."
          />

          <SummaryCard
            label="Approved"
            value={summary.approved}
            description="Final decisions authorizing the requested work."
            tone="emerald"
          />

          <SummaryCard
            label="Rejected"
            value={summary.rejected}
            description="Final decisions declining the requested authorization."
            tone="rose"
          />

          <SummaryCard
            label="With Decision Notes"
            value={summary.with_notes}
            description="Decisions carrying explicit recorded rationale or context."
            tone="indigo"
          />

        </section>


        {/* ==================================================
            COVERAGE STRIP
        ================================================== */}

        <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">

          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

            <div>

              <p className="text-sm font-semibold text-slate-900">
                Decision evidence coverage
              </p>

              <p className="mt-1 text-xs text-slate-500">
                Request evidence is shown separately from
                the authoritative decision fields.
              </p>

            </div>


            <div className="flex flex-wrap gap-2">

              <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
                Approved {summary.approved}
              </span>

              <span className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                Rejected {summary.rejected}
              </span>

              <span className="rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200">
                With Notes {summary.with_notes}
              </span>

              <span className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 ring-1 ring-inset ring-sky-200">
                Exact Request Evidence {summary.exact_request_evidence}
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
                  placeholder="Search decision, actor, requester, notes or evidence..."
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
                    "approved",
                    "rejected",
                  ].map(
                    (value) => (
                      <FilterButton
                        key={value}
                        active={
                          outcomeFilter ===
                          value
                        }
                        onClick={() =>
                          setOutcomeFilter(
                            value
                          )
                        }
                      >
                        {value === "all"
                          ? "All outcomes"
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
                          ? "All request evidence"
                          : EVIDENCE_META[
                              value
                            ]?.label}
                      </FilterButton>
                    )
                  )}

                </div>


                <div className="flex flex-wrap gap-2">

                  {[
                    "all",
                    "with_notes",
                    "without_notes",
                  ].map(
                    (value) => (
                      <FilterButton
                        key={value}
                        active={
                          notesFilter ===
                          value
                        }
                        onClick={() =>
                          setNotesFilter(
                            value
                          )
                        }
                      >
                        {value === "all"
                          ? "All notes"
                          : value ===
                            "with_notes"
                          ? "With decision notes"
                          : "Without decision notes"}
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
              DECISIONS REGISTER
          ================================================== */

          <section className="mt-6">

            {filteredItems.length === 0 ? (

              <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">

                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-700">

                  <Scale
                    size={24}
                  />

                </div>


                <h2 className="mt-4 text-lg font-semibold text-slate-900">

                  {items.length === 0
                    ? "No final decisions recorded"
                    : "No decisions match these filters"}

                </h2>


                <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">

                  {items.length === 0
                    ? "Approved and rejected approval outcomes will appear here once a final decision is recorded."
                    : "Adjust or clear your filters to return to the complete Decisions register."}

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
                    const outcome =
                      OUTCOME_META[
                        item.outcome
                      ] ||
                      OUTCOME_META.approved;

                    const OutcomeIcon =
                      outcome.icon;

                    const evidenceQuality =
                      item.request_evidence
                        ?.evidence_quality ||
                      "none";

                    const evidence =
                      EVIDENCE_META[
                        evidenceQuality
                      ] ||
                      EVIDENCE_META.none;

                    const evidenceText =
                      item.request_evidence
                        ?.evidence_text ||
                      "";

                    return (
                      <article
                        key={
                          item.decision_id
                        }
                        className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm transition hover:border-slate-300 hover:shadow-md"
                      >

                        <div className="grid xl:grid-cols-[minmax(0,1fr)_400px]">

                          {/* ================================
                              AUTHORITATIVE DECISION
                          ================================ */}

                          <div className="p-5 lg:p-6">

                            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">

                              <div className="min-w-0">

                                <div className="flex flex-wrap items-center gap-2">

                                  <Badge
                                    className={
                                      outcome.badge
                                    }
                                  >
                                    <OutcomeIcon
                                      size={12}
                                      className="mr-1.5"
                                    />

                                    {outcome.label}
                                  </Badge>


                                  <Badge
                                    className="border-indigo-200 bg-indigo-50 text-indigo-700"
                                  >
                                    <Scale
                                      size={12}
                                      className="mr-1.5"
                                    />

                                    Decision record
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
                                  {item.title ||
                                    "Recorded decision"}
                                </h2>


                                {item.description && (
                                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                                    {item.description}
                                  </p>
                                )}

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
                                DECISION PROVENANCE
                            ================================ */}

                            <div
                              className={`
                                mt-6 rounded-2xl border p-4
                                ${outcome.panel}
                              `}
                            >

                              <div className="flex items-center gap-2">

                                <OutcomeIcon
                                  size={17}
                                  className={
                                    item.outcome ===
                                    "approved"
                                      ? "text-emerald-700"
                                      : "text-rose-700"
                                  }
                                />

                                <p className="text-sm font-semibold text-slate-950">
                                  Authoritative decision record
                                </p>

                              </div>


                              <div className="mt-4 grid gap-4 sm:grid-cols-3">

                                <MetaField
                                  label="Outcome"
                                  value={
                                    outcome.label
                                  }
                                />

                                <MetaField
                                  label="Decision By"
                                  value={
                                    item.decision_by_email ||
                                    "Actor not recorded"
                                  }
                                />

                                <MetaField
                                  label="Decision At"
                                  value={formatDate(
                                    item.decision_at
                                  )}
                                />

                              </div>


                              <div className="mt-4 border-t border-slate-200/70 pt-4">

                                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                                  Decision Notes
                                </p>

                                <p className="mt-2 text-sm leading-6 text-slate-800">
                                  {item.decision_notes?.trim()
                                    ? item.decision_notes
                                    : "No decision notes were recorded."}
                                </p>

                              </div>

                            </div>


                            {/* ================================
                                REQUEST CONTEXT
                            ================================ */}

                            <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-4">

                              <div className="flex items-center gap-2">

                                <UserRound
                                  size={16}
                                  className="text-slate-400"
                                />

                                <p className="text-sm font-semibold text-slate-900">
                                  Approval request context
                                </p>

                              </div>


                              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

                                <MetaField
                                  label="Requested By"
                                  value={
                                    item.requested_by ||
                                    "Not recorded"
                                  }
                                />

                                <MetaField
                                  label="Assigned To"
                                  value={
                                    item.assigned_to_email ||
                                    "Not assigned"
                                  }
                                />

                                <MetaField
                                  label="Source Type"
                                  value={formatLabel(
                                    item.source_type
                                  )}
                                />

                                <MetaField
                                  label="Approval ID"
                                  value={String(
                                    item.approval_id
                                  )}
                                />

                              </div>

                            </div>

                          </div>


                          {/* ================================
                              REQUEST EVIDENCE
                          ================================ */}

                          <aside className="border-t border-slate-200 bg-slate-50/70 p-5 xl:border-l xl:border-t-0 xl:p-6">

                            <div className="flex items-center justify-between gap-3">

                              <div>

                                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                                  Approval request evidence
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
                                No exact request excerpt is
                                available for this decision.
                              </div>

                            )}


                            <div className="mt-5 border-t border-slate-200 pt-5">

                              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                                Request evidence provenance
                              </p>


                              <div className="mt-4 space-y-3">

                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Extraction method
                                  </span>

                                  <span className="text-right font-semibold text-slate-700">
                                    {formatLabel(
                                      item.request_evidence
                                        ?.extraction_method
                                    ) ||
                                      "Not available"}
                                  </span>

                                </div>


                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Processing mode
                                  </span>

                                  <span className="text-right font-semibold text-slate-700">
                                    {formatLabel(
                                      item.request_evidence
                                        ?.processing_mode
                                    ) ||
                                      "Not available"}
                                  </span>

                                </div>


                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Confidence
                                  </span>

                                  <span className="text-right font-semibold text-slate-700">
                                    {item.request_evidence
                                      ?.confidence ??
                                      "Not available"}
                                  </span>

                                </div>


                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Source message
                                  </span>

                                  <span className="text-right font-semibold text-slate-700">
                                    {item.source_message_id
                                      ? `#${item.source_message_id}`
                                      : "None"}
                                  </span>

                                </div>

                              </div>
                            </div>


                            <div className="mt-5 rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs leading-5 text-slate-600">

                              <strong className="text-slate-800">
                                Audit boundary:
                              </strong>{" "}
                              this evidence supports the
                              original approval request.
                              It is not represented as proof
                              that the final decision itself
                              occurred.

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
