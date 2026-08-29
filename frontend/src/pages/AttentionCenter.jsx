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
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
  User,
  Users,
} from "lucide-react";

import { useNavigate } from "react-router-dom";

import axios from "../axiosConfig";


const EMPTY_SUMMARY = {
  total: 0,
  critical: 0,
  high: 0,
  medium: 0,
  dropped_ball: 0,
  sla_at_risk: 0,
  ownership_gap: 0,
  internal: 0,
  counterparty: 0,
};


const SEVERITY_META = {
  critical: {
    label: "Critical",
    container:
      "border-rose-200 bg-rose-50 text-rose-700",
    dot:
      "bg-rose-500",
    card:
      "border-rose-200",
  },

  high: {
    label: "High",
    container:
      "border-amber-200 bg-amber-50 text-amber-800",
    dot:
      "bg-amber-500",
    card:
      "border-amber-200",
  },

  medium: {
    label: "Medium",
    container:
      "border-sky-200 bg-sky-50 text-sky-700",
    dot:
      "bg-sky-500",
    card:
      "border-slate-200",
  },
};


const CATEGORY_META = {
  dropped_ball: {
    label: "Dropped Ball",
    description:
      "A commitment has crossed an accountability boundary.",
  },

  sla_at_risk: {
    label: "SLA At Risk",
    description:
      "A communication commitment is approaching its response boundary.",
  },

  ownership_gap: {
    label: "Ownership Gap",
    description:
      "A pending internal commitment does not have valid explicit ownership.",
  },
};


const FILTER_BUTTON_BASE =
  "rounded-xl px-3.5 py-2 text-sm font-medium transition";


function formatDate(value) {
  if (!value) {
    return "Not set";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
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


function directionLabel(direction) {
  if (direction === "WE_OWE_THEM") {
    return "We owe them";
  }

  if (direction === "THEY_OWE_US") {
    return "They owe us";
  }

  return formatLabel(direction);
}


function evidenceQualityLabel(value) {
  if (value === "exact") {
    return "Exact source evidence";
  }

  if (value === "source_only") {
    return "Source-linked";
  }

  return "Evidence metadata";
}


function SummaryCard({
  label,
  value,
  description,
  tone = "slate",
}) {
  const toneClass = {
    slate:
      "border-slate-200 bg-white text-slate-950",

    rose:
      "border-rose-200 bg-gradient-to-br from-white to-rose-50 text-slate-950",

    amber:
      "border-amber-200 bg-gradient-to-br from-white to-amber-50 text-slate-950",

    sky:
      "border-sky-200 bg-gradient-to-br from-white to-sky-50 text-slate-950",
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

      <div className="mt-3 flex items-end justify-between gap-4">
        <p className="text-3xl font-semibold tracking-tight">
          {value}
        </p>

        <div className="h-2 w-2 rounded-full bg-slate-300" />
      </div>

      <p className="mt-2 text-xs leading-5 text-slate-500">
        {description}
      </p>
    </div>
  );
}


function FilterButton({
  active,
  children,
  onClick,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        ${FILTER_BUTTON_BASE}
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
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
        {label}
      </p>

      <p className="mt-1 text-sm font-medium text-slate-700">
        {value || "Not available"}
      </p>
    </div>
  );
}


export default function AttentionCenter() {
  const navigate = useNavigate();

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState("");

  const [items, setItems] =
    useState([]);

  const [summary, setSummary] =
    useState(EMPTY_SUMMARY);

  const [generatedAt, setGeneratedAt] =
    useState(null);

  const [search, setSearch] =
    useState("");

  const [categoryFilter, setCategoryFilter] =
    useState("all");

  const [severityFilter, setSeverityFilter] =
    useState("all");

  const [
    responsibilityFilter,
    setResponsibilityFilter,
  ] = useState("all");


  const fetchAttention = useCallback(
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

        const response = await axios.get(
          "/api/knowledge/attention/"
        );

        const payload =
          response.data || {};

        setItems(
          Array.isArray(payload.items)
            ? payload.items
            : []
        );

        setSummary({
          ...EMPTY_SUMMARY,
          ...(payload.summary || {}),
        });

        setGeneratedAt(
          payload.generated_at || null
        );
      } catch (err) {
        console.error(
          "Attention Center load error:",
          err
        );

        if (
          err.response?.status === 403
        ) {
          setError(
            "An active organization membership is required to view Attention Center."
          );
        } else {
          setError(
            "Unable to load Attention Center. Please refresh and try again."
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
    fetchAttention();
  }, [fetchAttention]);


  const filteredItems = useMemo(() => {
    const query =
      search.trim().toLowerCase();

    return items.filter((item) => {
      const matchesCategory =
        categoryFilter === "all" ||
        item.category === categoryFilter;

      const matchesSeverity =
        severityFilter === "all" ||
        item.severity === severityFilter;

      const matchesResponsibility =
        responsibilityFilter === "all" ||
        item.responsibility_side ===
          responsibilityFilter;

      const evidenceText =
        item.evidence?.evidence_text || "";

      const signals = Array.isArray(
        item.signal_codes
      )
        ? item.signal_codes.join(" ")
        : "";

      const searchable = [
        item.obligation,
        item.counterparty,
        item.owner_email,
        item.reason,
        item.reason_code,
        item.category,
        item.severity,
        evidenceText,
        signals,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !query ||
        searchable.includes(query);

      return (
        matchesCategory &&
        matchesSeverity &&
        matchesResponsibility &&
        matchesSearch
      );
    });
  }, [
    items,
    search,
    categoryFilter,
    severityFilter,
    responsibilityFilter,
  ]);


  const activeFilterCount = [
    categoryFilter !== "all",
    severityFilter !== "all",
    responsibilityFilter !== "all",
    search.trim() !== "",
  ].filter(Boolean).length;


  const clearFilters = () => {
    setSearch("");
    setCategoryFilter("all");
    setSeverityFilter("all");
    setResponsibilityFilter("all");
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


  const openWork = (item) => {
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
    <div className="min-h-full bg-slate-50">
      <div className="mx-auto max-w-[1500px] px-5 py-6 lg:px-8 lg:py-8">

        {/* ==================================================
            PREMIUM ENTERPRISE HEADER
        ================================================== */}

        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 shadow-xl shadow-slate-200/60">
          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl" />

          <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-sky-400/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">
            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">

              <div className="max-w-3xl">
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                  <ShieldCheck size={14} />
                  Accountability Intelligence
                </div>

                <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
                  Attention Center
                </h1>

                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                  A single evidence-backed view of commitments
                  requiring intervention now - without duplicate
                  alerts or reconstructed business logic.
                </p>

                <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-300">
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Evidence-backed
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Organization scoped
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    One item per commitment
                  </span>
                </div>
              </div>


              <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">

                {generatedAt && (
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Intelligence generated
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
                    fetchAttention({
                      background: true,
                    })
                  }
                  disabled={refreshing}
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
                    : "Refresh intelligence"}
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
                Attention intelligence unavailable
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
            label="Current attention"
            value={summary.total}
            description="Current commitments requiring intervention."
          />

          <SummaryCard
            label="Critical"
            value={summary.critical}
            description="Highest-priority internal accountability failures."
            tone="rose"
          />

          <SummaryCard
            label="High"
            value={summary.high}
            description="Urgent internal or counterparty attention."
            tone="amber"
          />

          <SummaryCard
            label="Medium"
            value={summary.medium}
            description="Ownership and accountability gaps requiring resolution."
            tone="sky"
          />
        </section>


        {/* ==================================================
            EXPOSURE BREAKDOWN
        ================================================== */}

        <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

            <div>
              <p className="text-sm font-semibold text-slate-900">
                Current exposure
              </p>

              <p className="mt-1 text-xs text-slate-500">
                Server-derived accountability categories and responsibility.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">

              <span className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                Dropped Ball {summary.dropped_ball}
              </span>

              <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
                SLA At Risk {summary.sla_at_risk}
              </span>

              <span className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 ring-1 ring-inset ring-sky-200">
                Ownership Gap {summary.ownership_gap}
              </span>

              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700">
                Internal {summary.internal}
              </span>

              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700">
                Counterparty {summary.counterparty}
              </span>
            </div>
          </div>
        </section>


        {/* ==================================================
            FILTER TOOLBAR
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
                  onChange={(event) =>
                    setSearch(
                      event.target.value
                    )
                  }
                  placeholder="Search obligation, counterparty, owner, reason or evidence..."
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

              <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">

                <div className="flex flex-wrap gap-2">
                  <FilterButton
                    active={
                      categoryFilter ===
                      "all"
                    }
                    onClick={() =>
                      setCategoryFilter(
                        "all"
                      )
                    }
                  >
                    All categories
                  </FilterButton>

                  <FilterButton
                    active={
                      categoryFilter ===
                      "dropped_ball"
                    }
                    onClick={() =>
                      setCategoryFilter(
                        "dropped_ball"
                      )
                    }
                  >
                    Dropped Ball
                  </FilterButton>

                  <FilterButton
                    active={
                      categoryFilter ===
                      "sla_at_risk"
                    }
                    onClick={() =>
                      setCategoryFilter(
                        "sla_at_risk"
                      )
                    }
                  >
                    SLA At Risk
                  </FilterButton>

                  <FilterButton
                    active={
                      categoryFilter ===
                      "ownership_gap"
                    }
                    onClick={() =>
                      setCategoryFilter(
                        "ownership_gap"
                      )
                    }
                  >
                    Ownership Gap
                  </FilterButton>
                </div>


                <div className="flex flex-wrap gap-2">
                  {[
                    "all",
                    "critical",
                    "high",
                    "medium",
                  ].map((value) => (
                    <FilterButton
                      key={value}
                      active={
                        severityFilter ===
                        value
                      }
                      onClick={() =>
                        setSeverityFilter(
                          value
                        )
                      }
                    >
                      {value === "all"
                        ? "All severity"
                        : formatLabel(
                            value
                          )}
                    </FilterButton>
                  ))}

                  {[
                    "all",
                    "internal",
                    "counterparty",
                  ].map((value) => (
                    <FilterButton
                      key={value}
                      active={
                        responsibilityFilter ===
                        value
                      }
                      onClick={() =>
                        setResponsibilityFilter(
                          value
                        )
                      }
                    >
                      {value === "all"
                        ? "All responsibility"
                        : formatLabel(
                            value
                          )}
                    </FilterButton>
                  ))}
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
              (item) => (
                <div
                  key={item}
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
              ATTENTION QUEUE
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
                    ? "Nothing needs attention right now"
                    : "No attention items match these filters"}
                </h2>

                <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
                  {items.length === 0
                    ? "One UCH currently has no active accountability findings for this organization."
                    : "Adjust or clear the filters to return to the complete attention queue."}
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
                    const severity =
                      SEVERITY_META[
                        item.severity
                      ] ||
                      SEVERITY_META.medium;

                    const category =
                      CATEGORY_META[
                        item.category
                      ] || {
                        label:
                          formatLabel(
                            item.category
                          ),
                        description:
                          item.reason || "",
                      };

                    const evidenceText =
                      item.evidence
                        ?.evidence_text || "";

                    const evidenceQuality =
                      item.evidence
                        ?.evidence_quality ||
                      "none";

                    const signalCodes =
                      Array.isArray(
                        item.signal_codes
                      )
                        ? item.signal_codes
                        : [];

                    return (
                      <article
                        key={
                          item.attention_id
                        }
                        className={`
                          overflow-hidden rounded-[24px] border bg-white shadow-sm transition hover:shadow-md
                          ${severity.card}
                        `}
                      >
                        <div className="grid xl:grid-cols-[minmax(0,1fr)_360px]">

                          {/* ================================
                              PRIMARY
                          ================================ */}

                          <div className="p-5 lg:p-6">

                            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

                              <div className="min-w-0">

                                <div className="flex flex-wrap items-center gap-2">

                                  <span
                                    className={`
                                      inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold
                                      ${severity.container}
                                    `}
                                  >
                                    <span
                                      className={`
                                        h-1.5 w-1.5 rounded-full
                                        ${severity.dot}
                                      `}
                                    />

                                    {severity.label}
                                  </span>

                                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
                                    {category.label}
                                  </span>

                                  <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-500">
                                    {directionLabel(
                                      item.direction
                                    )}
                                  </span>

                                  <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-500">
                                    {formatLabel(
                                      item.responsibility_side
                                    )}
                                  </span>
                                </div>


                                <h2 className="mt-4 text-xl font-semibold tracking-tight text-slate-950">
                                  {item.obligation ||
                                    "Communication commitment"}
                                </h2>

                                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                                  {item.reason ||
                                    category.description}
                                </p>
                              </div>


                              <div className="flex shrink-0 gap-2">

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
                                      openWork(
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
                                label="Owner"
                                value={
                                  item.owner_email ||
                                  "Unassigned"
                                }
                              />

                              <MetaField
                                label="Commitment due"
                                value={formatDate(
                                  item.commitment_due_at
                                )}
                              />

                              <MetaField
                                label="Communication SLA"
                                value={formatDate(
                                  item.sla_due_at
                                )}
                              />
                            </div>


                            {/* ================================
                                SIGNALS
                            ================================ */}

                            {signalCodes.length >
                              0 && (
                              <div className="mt-5">

                                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                                  Accountability signals
                                </p>

                                <div className="mt-2.5 flex flex-wrap gap-2">
                                  {signalCodes.map(
                                    (
                                      signal
                                    ) => (
                                      <span
                                        key={
                                          signal
                                        }
                                        className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600"
                                      >
                                        {formatLabel(
                                          signal
                                        )}
                                      </span>
                                    )
                                  )}
                                </div>
                              </div>
                            )}
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
                                  {evidenceQualityLabel(
                                    evidenceQuality
                                  )}
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
                                Source communication is linked, but an exact excerpt is not available for this historical item.
                              </div>
                            )}


                            <div className="mt-5 space-y-3 border-t border-slate-200 pt-4">

                              <div className="flex items-center justify-between gap-4 text-xs">
                                <span className="text-slate-500">
                                  Evidence quality
                                </span>

                                <span className="font-semibold text-slate-700">
                                  {formatLabel(
                                    evidenceQuality
                                  )}
                                </span>
                              </div>


                              <div className="flex items-center justify-between gap-4 text-xs">
                                <span className="text-slate-500">
                                  Confidence
                                </span>

                                <span className="font-semibold text-slate-700">
                                  {item.evidence
                                    ?.confidence ??
                                    0}
                                  %
                                </span>
                              </div>


                              <div className="flex items-center justify-between gap-4 text-xs">
                                <span className="text-slate-500">
                                  Extraction
                                </span>

                                <span className="font-semibold text-slate-700">
                                  {formatLabel(
                                    item.evidence
                                      ?.extraction_method ||
                                      "unknown"
                                  )}
                                </span>
                              </div>


                              {item.owner_email ? (
                                <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs text-slate-600">
                                  <User
                                    size={14}
                                  />
                                  Explicit owner assigned
                                </div>
                              ) : item.responsibility_side ===
                                "internal" ? (
                                <div className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs font-medium text-amber-800">
                                  <Users
                                    size={14}
                                  />
                                  Internal ownership requires attention
                                </div>
                              ) : (
                                <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs text-slate-600">
                                  <Clock
                                    size={14}
                                  />
                                  Waiting on counterparty
                                </div>
                              )}
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
