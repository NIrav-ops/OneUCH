import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  AlertTriangle,
  ArrowUpRight,
  Briefcase,
  CheckCircle2,
  Clock,
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";

import {
  useNavigate,
} from "react-router-dom";

import axios from "../axiosConfig";


const EMPTY_SUMMARY = {
  total: 0,
  actions: 0,
  approvals: 0,
  overdue: 0,
  due_today: 0,
  in_progress: 0,
  blocked: 0,
  waiting: 0,
  needs_info: 0,
  no_due: 0,
};


const TYPE_META = {
  action: {
    label: "Action",
    badge:
      "border-indigo-200 bg-indigo-50 text-indigo-700",
  },

  approval: {
    label: "Approval",
    badge:
      "border-violet-200 bg-violet-50 text-violet-700",
  },
};


const DUE_META = {
  overdue: {
    label: "Overdue",
    badge:
      "border-rose-200 bg-rose-50 text-rose-700",
    dot:
      "bg-rose-500",
  },

  due_today: {
    label: "Due Today",
    badge:
      "border-amber-200 bg-amber-50 text-amber-800",
    dot:
      "bg-amber-500",
  },

  upcoming: {
    label: "Upcoming",
    badge:
      "border-sky-200 bg-sky-50 text-sky-700",
    dot:
      "bg-sky-500",
  },

  no_due: {
    label: "No Due Date",
    badge:
      "border-slate-200 bg-slate-50 text-slate-600",
    dot:
      "bg-slate-400",
  },
};


const STATUS_META = {
  open: {
    label: "Open",
    badge:
      "border-slate-200 bg-white text-slate-700",
  },

  in_progress: {
    label: "In Progress",
    badge:
      "border-blue-200 bg-blue-50 text-blue-700",
  },

  waiting: {
    label: "Waiting",
    badge:
      "border-amber-200 bg-amber-50 text-amber-700",
  },

  blocked: {
    label: "Blocked",
    badge:
      "border-rose-200 bg-rose-50 text-rose-700",
  },

  pending: {
    label: "Pending",
    badge:
      "border-violet-200 bg-violet-50 text-violet-700",
  },

  needs_info: {
    label: "Needs Info",
    badge:
      "border-orange-200 bg-orange-50 text-orange-700",
  },
};


function formatDate(value) {
  if (!value) {
    return "No due date";
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

    rose:
      "border-rose-200 bg-gradient-to-br from-white to-rose-50",

    amber:
      "border-amber-200 bg-gradient-to-br from-white to-amber-50",

    violet:
      "border-violet-200 bg-gradient-to-br from-white to-violet-50",
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


export default function MyWork() {
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

  const [typeFilter, setTypeFilter] =
    useState("all");

  const [dueFilter, setDueFilter] =
    useState("all");

  const [
    statusFilter,
    setStatusFilter,
  ] = useState("all");


  const loadMyWork = useCallback(
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
            "/api/my-work/"
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
          "My Work load error:",
          err
        );

        if (
          err.response?.status ===
          403
        ) {
          setError(
            "An active organization membership is required to view My Work."
          );
        } else {
          setError(
            "Unable to load My Work. Please refresh and try again."
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
    loadMyWork();
  }, [loadMyWork]);


  const filteredItems =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      return items.filter(
        (item) => {
          const matchesType =
            typeFilter === "all" ||
            item.work_type ===
              typeFilter;

          const matchesDue =
            dueFilter === "all" ||
            item.due_state ===
              dueFilter;

          const matchesStatus =
            statusFilter ===
              "all" ||
            item.status ===
              statusFilter;

          const searchable = [
            item.title,
            item.description,
            item.owner_email,
            item.status,
            item.work_type,
            item.due_state,
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
            matchesType &&
            matchesDue &&
            matchesStatus &&
            matchesSearch
          );
        }
      );
    }, [
      items,
      search,
      typeFilter,
      dueFilter,
      statusFilter,
    ]);


  const activeFilterCount = [
    search.trim() !== "",
    typeFilter !== "all",
    dueFilter !== "all",
    statusFilter !== "all",
  ].filter(Boolean).length;


  const clearFilters = () => {
    setSearch("");
    setTypeFilter("all");
    setDueFilter("all");
    setStatusFilter("all");
  };


  const openSource = (
    item
  ) => {
    if (!item.open_url) {
      return;
    }

    navigate(
      item.open_url
    );
  };


  const openExecution = (
    item
  ) => {
    if (!item.execution_url) {
      return;
    }

    navigate(
      item.execution_url
    );
  };


  return (
    <div className="min-h-full bg-slate-50">

      <div className="mx-auto max-w-[1500px] px-5 py-6 lg:px-8 lg:py-8">

        {/* ==================================================
            HERO
        ================================================== */}

        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 shadow-xl shadow-slate-200/60">

          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-violet-500/10 blur-3xl" />

          <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-blue-400/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">

              <div className="max-w-3xl">

                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                  <Briefcase
                    size={14}
                  />
                  Personal Execution
                </div>

                <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
                  My Work
                </h1>

                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                  Your explicitly owned execution queue across
                  actions and approvals, prioritized by the
                  server without inferred responsibility.
                </p>

                <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-300">

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Explicit ownership
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Organization scoped
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Server prioritized
                  </span>

                </div>
              </div>


              <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">

                {generatedAt && (
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5">

                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Work generated
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
                    loadMyWork({
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
                    : "Refresh work"}

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
                My Work unavailable
              </p>

              <p className="mt-1 text-rose-700">
                {error}
              </p>
            </div>

          </div>
        )}


        {/* ==================================================
            EXECUTION SUMMARY
        ================================================== */}

        <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          <SummaryCard
            label="Active Work"
            value={summary.total}
            description="Explicitly owned actions and approvals."
          />

          <SummaryCard
            label="Due Today"
            value={summary.due_today}
            description="Work the server has classified as due today."
            tone="amber"
          />

          <SummaryCard
            label="Overdue"
            value={summary.overdue}
            description="Owned work already past its due boundary."
            tone="rose"
          />

          <SummaryCard
            label="Approvals"
            value={summary.approvals}
            description="Approval decisions currently assigned to you."
            tone="violet"
          />

        </section>


        {/* ==================================================
            STATUS STRIP
        ================================================== */}

        <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">

          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

            <div>
              <p className="text-sm font-semibold text-slate-900">
                Execution state
              </p>

              <p className="mt-1 text-xs text-slate-500">
                Current server-owned work state across your queue.
              </p>
            </div>


            <div className="flex flex-wrap gap-2">

              <span className="rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200">
                Actions {summary.actions}
              </span>

              <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-200">
                In Progress {summary.in_progress}
              </span>

              <span className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                Blocked {summary.blocked}
              </span>

              <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
                Waiting {summary.waiting}
              </span>

              <span className="rounded-full bg-orange-50 px-3 py-1.5 text-xs font-medium text-orange-700 ring-1 ring-inset ring-orange-200">
                Needs Info {summary.needs_info}
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
                  placeholder="Search title, description, owner or status..."
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

                  {[
                    "all",
                    "action",
                    "approval",
                  ].map(
                    (value) => (
                      <FilterButton
                        key={value}
                        active={
                          typeFilter ===
                          value
                        }
                        onClick={() =>
                          setTypeFilter(
                            value
                          )
                        }
                      >
                        {value === "all"
                          ? "All work"
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
                          : formatLabel(
                              value
                            )}
                      </FilterButton>
                    )
                  )}

                </div>
              </div>


              <div className="mt-3 flex flex-wrap gap-2">

                {[
                  "all",
                  "open",
                  "in_progress",
                  "pending",
                  "blocked",
                  "waiting",
                  "needs_info",
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
                  <div className="h-4 w-28 rounded bg-slate-200" />

                  <div className="mt-5 h-6 w-2/3 rounded bg-slate-200" />

                  <div className="mt-3 h-4 w-full rounded bg-slate-100" />

                  <div className="mt-2 h-4 w-4/5 rounded bg-slate-100" />
                </div>
              )
            )}

          </div>
        ) : (

          /* ==================================================
              EXECUTION QUEUE
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
                    ? "Your active work queue is clear"
                    : "No work matches these filters"}
                </h2>

                <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
                  {items.length === 0
                    ? "One UCH currently has no active actions or approvals explicitly assigned to you."
                    : "Adjust or clear your filters to return to the complete execution queue."}
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
                    const type =
                      TYPE_META[
                        item.work_type
                      ] || {
                        label:
                          formatLabel(
                            item.work_type
                          ),
                        badge:
                          "border-slate-200 bg-slate-50 text-slate-700",
                      };

                    const due =
                      DUE_META[
                        item.due_state
                      ] ||
                      DUE_META.no_due;

                    const status =
                      STATUS_META[
                        item.status
                      ] || {
                        label:
                          formatLabel(
                            item.status
                          ),
                        badge:
                          "border-slate-200 bg-white text-slate-700",
                      };

                    return (
                      <article
                        key={
                          item.work_id
                        }
                        className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm transition hover:border-slate-300 hover:shadow-md"
                      >

                        <div className="grid xl:grid-cols-[minmax(0,1fr)_320px]">

                          {/* ================================
                              MAIN
                          ================================ */}

                          <div className="p-5 lg:p-6">

                            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">

                              <div className="min-w-0">

                                <div className="flex flex-wrap items-center gap-2">

                                  <Badge
                                    className={
                                      type.badge
                                    }
                                  >
                                    {type.label}
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
                                      status.badge
                                    }
                                  >
                                    {status.label}
                                  </Badge>

                                </div>


                                <h2 className="mt-4 text-xl font-semibold tracking-tight text-slate-950">
                                  {item.title ||
                                    "Untitled work item"}
                                </h2>


                                {item.description && (
                                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                                    {item.description}
                                  </p>
                                )}

                              </div>


                              <div className="flex shrink-0 flex-wrap gap-2">

                                {item.open_url && (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      openSource(
                                        item
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


                                <button
                                  type="button"
                                  onClick={() =>
                                    openExecution(
                                      item
                                    )
                                  }
                                  className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
                                >
                                  {item.work_type ===
                                  "approval"
                                    ? "Review Approval"
                                    : "Open Action"}

                                  <ArrowUpRight
                                    size={15}
                                  />
                                </button>

                              </div>
                            </div>


                            {/* ================================
                                EXECUTION DETAILS
                            ================================ */}

                            <div className="mt-6 grid gap-4 rounded-2xl border border-slate-100 bg-slate-50/70 p-4 sm:grid-cols-2 lg:grid-cols-4">

                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Owner
                                </p>

                                <p className="mt-1 text-sm font-medium text-slate-700">
                                  {item.owner_email ||
                                    "Not available"}
                                </p>
                              </div>


                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Due
                                </p>

                                <p className="mt-1 text-sm font-medium text-slate-700">
                                  {formatDate(
                                    item.due_at
                                  )}
                                </p>
                              </div>


                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Priority
                                </p>

                                <p className="mt-1 text-sm font-medium text-slate-700">
                                  {item.priority ??
                                    0}
                                </p>
                              </div>


                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Work ID
                                </p>

                                <p className="mt-1 truncate text-sm font-medium text-slate-700">
                                  {item.work_id}
                                </p>
                              </div>

                            </div>
                          </div>


                          {/* ================================
                              RIGHT EXECUTION PANEL
                          ================================ */}

                          <aside className="border-t border-slate-200 bg-slate-50/70 p-5 xl:border-l xl:border-t-0 xl:p-6">

                            <div className="flex items-center justify-between">

                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                                  Execution context
                                </p>

                                <p className="mt-1 text-sm font-semibold text-slate-800">
                                  {type.label}
                                </p>
                              </div>

                              <ShieldCheck
                                size={18}
                                className="text-slate-400"
                              />

                            </div>


                            <div className="mt-5 space-y-3">

                              <div className="flex items-center justify-between gap-4 text-xs">

                                <span className="text-slate-500">
                                  Due state
                                </span>

                                <span className="font-semibold text-slate-700">
                                  {due.label}
                                </span>

                              </div>


                              <div className="flex items-center justify-between gap-4 text-xs">

                                <span className="text-slate-500">
                                  Status
                                </span>

                                <span className="font-semibold text-slate-700">
                                  {status.label}
                                </span>

                              </div>


                              <div className="flex items-center justify-between gap-4 text-xs">

                                <span className="text-slate-500">
                                  Source object
                                </span>

                                <span className="font-semibold text-slate-700">
                                  #{item.source_object_id}
                                </span>

                              </div>


                              {item.source_message_id && (
                                <div className="flex items-center justify-between gap-4 text-xs">

                                  <span className="text-slate-500">
                                    Source message
                                  </span>

                                  <span className="font-semibold text-slate-700">
                                    #{item.source_message_id}
                                  </span>

                                </div>
                              )}

                            </div>


                            <div
                              className={`
                                mt-5 flex items-start gap-2 rounded-xl border px-3 py-3 text-xs font-medium
                                ${
                                  item.due_state ===
                                  "overdue"
                                    ? "border-rose-200 bg-rose-50 text-rose-800"
                                    : item.due_state ===
                                      "due_today"
                                    ? "border-amber-200 bg-amber-50 text-amber-800"
                                    : "border-slate-200 bg-white text-slate-600"
                                }
                              `}
                            >

                              <Clock
                                size={14}
                                className="mt-0.5 shrink-0"
                              />

                              <span>
                                {item.due_state ===
                                "overdue"
                                  ? "This owned work is past its server-classified due boundary."
                                  : item.due_state ===
                                    "due_today"
                                  ? "This owned work is due today."
                                  : "This item remains in your active execution queue."}
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
