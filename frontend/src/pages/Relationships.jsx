import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  AlertTriangle,
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  CalendarClock,
  CheckCircle2,
  Clock3,
  Handshake,
  History,
  Mail,
  MessagesSquare,
  RefreshCw,
  Scale,
  Search,
  UserRound,
  Users,
  XCircle,
} from "lucide-react";

import {
  useNavigate,
} from "react-router-dom";

import axios from "../axiosConfig";


const EMPTY_SUMMARY = {
  total_profiles: 0,
  with_communication_history: 0,
  with_pending_commitments: 0,
  with_active_waits: 0,
  with_decisions: 0,
};


const FILTERS = [
  {
    value: "all",
    label: "All relationships",
  },
  {
    value: "accountability",
    label: "Pending commitments",
  },
  {
    value: "waiting",
    label: "Active waits",
  },
  {
    value: "decisions",
    label: "With decisions",
  },
  {
    value: "known_identity",
    label: "Known identity",
  },
];


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


function displayName(profile) {
  return (
    profile?.full_name?.trim() ||
    profile?.email ||
    "External relationship"
  );
}


function displayCompany(profile) {
  return (
    profile?.company?.trim() ||
    profile?.domain ||
    "Organization not identified"
  );
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

    sky:
      "border-sky-200 bg-gradient-to-br from-white to-sky-50",

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


function Metric({
  label,
  value,
  description,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
        {label}
      </p>

      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>

      <p className="mt-1 text-xs leading-5 text-slate-500">
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
        rounded-xl px-3 py-2 text-xs font-semibold transition
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


function SectionHeader({
  icon,
  title,
  description,
  count,
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">

        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
          {icon}
        </div>

        <div>
          <p className="text-sm font-semibold text-slate-950">
            {title}
          </p>

          <p className="mt-1 text-xs leading-5 text-slate-500">
            {description}
          </p>
        </div>
      </div>

      {count !== undefined && (
        <span className="self-start rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 sm:self-auto">
          {count}
        </span>
      )}
    </div>
  );
}


export default function Relationships() {
  const navigate =
    useNavigate();

  const [loading, setLoading] =
    useState(true);

  const [
    detailLoading,
    setDetailLoading,
  ] = useState(false);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [error, setError] =
    useState("");

  const [profiles, setProfiles] =
    useState([]);

  const [summary, setSummary] =
    useState(EMPTY_SUMMARY);

  const [
    selectedEmail,
    setSelectedEmail,
  ] = useState("");

  const [
    selectedPayload,
    setSelectedPayload,
  ] = useState(null);

  const [search, setSearch] =
    useState("");

  const [
    relationshipFilter,
    setRelationshipFilter,
  ] = useState("all");


  const loadIndex =
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
              "/api/knowledge/relationships/"
            );

          const payload =
            response.data || {};

          const nextProfiles =
            Array.isArray(
              payload.profiles
            )
              ? payload.profiles
              : [];

          setProfiles(
            nextProfiles
          );

          setSummary({
            ...EMPTY_SUMMARY,
            ...(payload.summary || {}),
          });

          setSelectedEmail(
            (current) => {
              if (
                current &&
                nextProfiles.some(
                  (profile) =>
                    profile.email ===
                    current
                )
              ) {
                return current;
              }

              return (
                nextProfiles[0]
                  ?.email ||
                ""
              );
            }
          );
        } catch (err) {
          console.error(
            "Relationship index load error:",
            err
          );

          if (
            err.response?.status ===
            403
          ) {
            setError(
              "An active organization membership is required to view Relationships."
            );
          } else {
            setError(
              "Unable to load relationship intelligence. Please refresh and try again."
            );
          }
        } finally {
          setLoading(false);

          if (background) {
            setRefreshing(false);
          }
        }
      },
      []
    );


  const loadProfile =
    useCallback(
      async (
        email,
        {
          background = false,
        } = {}
      ) => {
        if (!email) {
          setSelectedPayload(null);
          return;
        }

        try {
          if (!background) {
            setDetailLoading(true);
          }

          const response =
            await axios.get(
              "/api/knowledge/relationships/",
              {
                params: {
                  email,
                },
              }
            );

          setSelectedPayload(
            response.data ||
              null
          );
        } catch (err) {
          console.error(
            "Relationship profile load error:",
            err
          );

          setSelectedPayload(null);

          if (
            err.response?.status !==
            404
          ) {
            setError(
              "Unable to load the selected relationship profile."
            );
          }
        } finally {
          setDetailLoading(false);
        }
      },
      []
    );


  useEffect(() => {
    loadIndex();
  }, [loadIndex]);


  useEffect(() => {
    if (selectedEmail) {
      loadProfile(
        selectedEmail
      );
    } else {
      setSelectedPayload(
        null
      );
    }
  }, [
    selectedEmail,
    loadProfile,
  ]);


  const refreshAll =
    async () => {
      setRefreshing(true);

      try {
        await loadIndex({
          background: true,
        });

        if (selectedEmail) {
          await loadProfile(
            selectedEmail,
            {
              background: true,
            }
          );
        }
      } finally {
        setRefreshing(false);
      }
    };


  const filteredProfiles =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      return profiles.filter(
        (profile) => {
          const matchesSearch =
            !query ||
            [
              profile.full_name,
              profile.email,
              profile.company,
              profile.job_title,
              profile.domain,
            ]
              .filter(Boolean)
              .join(" ")
              .toLowerCase()
              .includes(
                query
              );

          const matchesFilter =
            relationshipFilter ===
              "all" ||
            (
              relationshipFilter ===
                "accountability" &&
              profile
                .pending_commitments >
                0
            ) ||
            (
              relationshipFilter ===
                "waiting" &&
              profile.active_waits >
                0
            ) ||
            (
              relationshipFilter ===
                "decisions" &&
              profile.decisions >
                0
            ) ||
            (
              relationshipFilter ===
                "known_identity" &&
              Boolean(
                profile.person_id
              )
            );

          return (
            matchesSearch &&
            matchesFilter
          );
        }
      );
    }, [
      profiles,
      search,
      relationshipFilter,
    ]);


  const selected =
    selectedPayload
      ?.profile ||
    profiles.find(
      (profile) =>
        profile.email ===
        selectedEmail
    ) ||
    null;


  const communications =
    selectedPayload
      ?.recent_communications ||
    [];

  const commitments =
    selectedPayload
      ?.commitments ||
    [];

  const waitingFor =
    selectedPayload
      ?.waiting_for ||
    [];

  const decisions =
    selectedPayload
      ?.decisions ||
    [];


  const openUrl = (
    url
  ) => {
    if (!url) {
      return;
    }

    navigate(
      url
    );
  };


  return (
    <div className="min-h-full bg-slate-50">

      <div className="mx-auto max-w-[1580px] px-5 py-6 lg:px-8 lg:py-8">

        {/* ==================================================
            HERO
        ================================================== */}

        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 shadow-xl shadow-slate-200/60">

          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-violet-500/10 blur-3xl" />

          <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-sky-500/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">

              <div className="max-w-3xl">

                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">

                  <Users
                    size={14}
                  />

                  Relationship Intelligence

                </div>


                <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
                  Relationships
                </h1>


                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                  A factual operational profile of the external
                  people your organization communicates with,
                  combining communication history, commitments,
                  outstanding responses and recorded decisions.
                </p>


                <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-300">

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Email identity
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Observed communication
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    Accountability connected
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                    No synthetic health score
                  </span>

                </div>

              </div>


              <button
                type="button"
                onClick={
                  refreshAll
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
                  : "Refresh intelligence"}

              </button>

            </div>
          </div>
        </section>


        {/* ==================================================
            TRUTH BOUNDARY
        ================================================== */}

        <section className="mt-4 rounded-2xl border border-sky-200 bg-sky-50/70 px-5 py-4">

          <div className="flex items-start gap-3">

            <History
              size={18}
              className="mt-0.5 shrink-0 text-sky-700"
            />

            <div>

              <p className="text-sm font-semibold text-sky-950">
                Observed relationship context, not inferred sentiment
              </p>

              <p className="mt-1 text-xs leading-5 text-sky-800">
                This workspace summarizes communication and
                accountability already recorded by One UCH.
                It does not invent relationship health, trust,
                sentiment or risk scores.
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
                Relationship intelligence unavailable
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
            label="External Relationships"
            value={
              summary.total_profiles
            }
            description="External identities known through Person records or communication activity."
          />

          <SummaryCard
            label="Communication History"
            value={
              summary.with_communication_history
            }
            description="Relationships with observed inbound or outbound communication."
            tone="sky"
          />

          <SummaryCard
            label="Pending Commitments"
            value={
              summary.with_pending_commitments
            }
            description="Relationships connected to one or more pending commitments."
            tone="amber"
          />

          <SummaryCard
            label="Active Waits"
            value={
              summary.with_active_waits
            }
            description="Relationships from whom an external obligation remains outstanding."
            tone="violet"
          />

        </section>


        <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

            <div>
              <p className="text-sm font-semibold text-slate-900">
                Relationship coverage
              </p>

              <p className="mt-1 text-xs text-slate-500">
                Directory ordering comes from the backend relationship projection.
              </p>
            </div>


            <div className="flex flex-wrap gap-2">

              <span className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 ring-1 ring-inset ring-sky-200">
                Communication {summary.with_communication_history}
              </span>

              <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
                Pending Commitments {summary.with_pending_commitments}
              </span>

              <span className="rounded-full bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-700 ring-1 ring-inset ring-violet-200">
                Active Waits {summary.with_active_waits}
              </span>

              <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
                Decisions {summary.with_decisions}
              </span>

            </div>
          </div>
        </section>


        {/* ==================================================
            MAIN WORKSPACE
        ================================================== */}

        <section className="mt-6 grid gap-5 xl:grid-cols-[370px_minmax(0,1fr)]">

          {/* ==================================================
              DIRECTORY
          ================================================== */}

          <aside className="min-w-0">

            <div className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm">

              <div className="border-b border-slate-200 p-4">

                <div className="flex items-center justify-between gap-3">

                  <div>
                    <p className="text-sm font-semibold text-slate-950">
                      Relationship Directory
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {filteredProfiles.length} of {profiles.length} visible
                    </p>
                  </div>


                  <Users
                    size={19}
                    className="text-slate-400"
                  />

                </div>


                <div className="relative mt-4">

                  <Search
                    size={16}
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
                    placeholder="Search person, company or email..."
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:bg-white"
                  />

                </div>


                <div className="mt-3 flex flex-wrap gap-2">

                  {FILTERS.map(
                    (filter) => (
                      <FilterButton
                        key={
                          filter.value
                        }
                        active={
                          relationshipFilter ===
                          filter.value
                        }
                        onClick={() =>
                          setRelationshipFilter(
                            filter.value
                          )
                        }
                      >
                        {filter.label}
                      </FilterButton>
                    )
                  )}

                </div>

              </div>


              {loading ? (

                <div className="space-y-3 p-4">

                  {[1, 2, 3, 4].map(
                    (item) => (
                      <div
                        key={item}
                        className="animate-pulse rounded-2xl border border-slate-100 p-4"
                      >
                        <div className="h-4 w-40 rounded bg-slate-200" />
                        <div className="mt-2 h-3 w-52 rounded bg-slate-100" />
                        <div className="mt-4 h-8 rounded bg-slate-100" />
                      </div>
                    )
                  )}

                </div>

              ) : filteredProfiles.length === 0 ? (

                <div className="px-5 py-10 text-center">

                  <Users
                    size={25}
                    className="mx-auto text-slate-300"
                  />

                  <p className="mt-3 text-sm font-semibold text-slate-800">
                    No relationships match
                  </p>

                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    Change the search or filter to see other external relationships.
                  </p>

                </div>

              ) : (

                <div className="max-h-[980px] overflow-y-auto p-2">

                  {filteredProfiles.map(
                    (profile) => {
                      const active =
                        profile.email ===
                        selectedEmail;

                      return (
                        <button
                          key={
                            profile.relationship_id
                          }
                          type="button"
                          onClick={() =>
                            setSelectedEmail(
                              profile.email
                            )
                          }
                          className={`
                            mb-2 w-full rounded-2xl border p-4 text-left transition
                            ${
                              active
                                ? "border-slate-900 bg-slate-950 text-white shadow-md"
                                : "border-slate-100 bg-white hover:border-slate-300 hover:bg-slate-50"
                            }
                          `}
                        >

                          <div className="flex items-start justify-between gap-3">

                            <div className="min-w-0">

                              <p
                                className={`
                                  truncate text-sm font-semibold
                                  ${
                                    active
                                      ? "text-white"
                                      : "text-slate-950"
                                  }
                                `}
                              >
                                {displayName(
                                  profile
                                )}
                              </p>

                              <p
                                className={`
                                  mt-1 break-all text-xs
                                  ${
                                    active
                                      ? "text-slate-300"
                                      : "text-slate-500"
                                  }
                                `}
                              >
                                {profile.email}
                              </p>

                            </div>


                            {profile.person_id ? (
                              <UserRound
                                size={16}
                                className={
                                  active
                                    ? "shrink-0 text-emerald-300"
                                    : "shrink-0 text-emerald-600"
                                }
                              />
                            ) : (
                              <Mail
                                size={16}
                                className={
                                  active
                                    ? "shrink-0 text-slate-400"
                                    : "shrink-0 text-slate-400"
                                }
                              />
                            )}

                          </div>


                          <p
                            className={`
                              mt-2 truncate text-xs
                              ${
                                active
                                  ? "text-slate-300"
                                  : "text-slate-500"
                              }
                            `}
                          >
                            {displayCompany(
                              profile
                            )}
                          </p>


                          <div className="mt-4 grid grid-cols-3 gap-2">

                            <div
                              className={`
                                rounded-lg px-2 py-2
                                ${
                                  active
                                    ? "bg-white/10"
                                    : "bg-slate-50"
                                }
                              `}
                            >
                              <p className="text-[10px] uppercase tracking-wide opacity-60">
                                Messages
                              </p>

                              <p className="mt-1 text-sm font-semibold">
                                {profile.communication_total}
                              </p>
                            </div>


                            <div
                              className={`
                                rounded-lg px-2 py-2
                                ${
                                  active
                                    ? "bg-white/10"
                                    : "bg-slate-50"
                                }
                              `}
                            >
                              <p className="text-[10px] uppercase tracking-wide opacity-60">
                                Pending
                              </p>

                              <p className="mt-1 text-sm font-semibold">
                                {profile.pending_commitments}
                              </p>
                            </div>


                            <div
                              className={`
                                rounded-lg px-2 py-2
                                ${
                                  active
                                    ? "bg-white/10"
                                    : "bg-slate-50"
                                }
                              `}
                            >
                              <p className="text-[10px] uppercase tracking-wide opacity-60">
                                Waits
                              </p>

                              <p className="mt-1 text-sm font-semibold">
                                {profile.active_waits}
                              </p>
                            </div>

                          </div>


                          <div
                            className={`
                              mt-3 flex items-center justify-between gap-3 text-[11px]
                              ${
                                active
                                  ? "text-slate-300"
                                  : "text-slate-500"
                              }
                            `}
                          >
                            <span>
                              {profile.last_interaction_at
                                ? `Last: ${formatDate(
                                    profile.last_interaction_at
                                  )}`
                                : "No communication yet"}
                            </span>

                            <ArrowRight
                              size={14}
                              className="shrink-0"
                            />
                          </div>

                        </button>
                      );
                    }
                  )}

                </div>
              )}

            </div>
          </aside>


          {/* ==================================================
              PROFILE
          ================================================== */}

          <div className="min-w-0">

            {!selected ? (

              <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">

                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-600">
                  <UserRound size={24} />
                </div>

                <h2 className="mt-4 text-lg font-semibold text-slate-900">
                  Select a relationship
                </h2>

                <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
                  Choose an external relationship from the directory to view its communication and accountability profile.
                </p>

              </div>

            ) : (

              <div className="space-y-5">

                {/* ============================================
                    IDENTITY
                ============================================ */}

                <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

                  <div className="border-b border-slate-200 bg-gradient-to-r from-white to-slate-50 px-5 py-5 lg:px-6">

                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">

                      <div className="flex min-w-0 items-start gap-4">

                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white">
                          <UserRound size={22} />
                        </div>


                        <div className="min-w-0">

                          <div className="flex flex-wrap items-center gap-2">

                            <h2 className="break-words text-xl font-semibold tracking-tight text-slate-950">
                              {displayName(
                                selected
                              )}
                            </h2>


                            {selected.person_id ? (
                              <Badge className="border-emerald-200 bg-emerald-50 text-emerald-700">
                                Known Person
                              </Badge>
                            ) : (
                              <Badge className="border-slate-200 bg-slate-50 text-slate-600">
                                Communication Identity
                              </Badge>
                            )}

                          </div>


                          <p className="mt-1 break-all text-sm text-slate-600">
                            {selected.email}
                          </p>


                          <p className="mt-2 text-sm font-medium text-slate-700">
                            {displayCompany(
                              selected
                            )}
                          </p>

                        </div>
                      </div>


                      {selected.open_url && (
                        <button
                          type="button"
                          onClick={() =>
                            openUrl(
                              selected.open_url
                            )
                          }
                          className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
                        >
                          <Mail size={15} />
                          Open Latest Email
                        </button>
                      )}

                    </div>


                    <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

                      <MetaField
                        label="Company"
                        value={
                          selected.company ||
                          "Not identified"
                        }
                      />

                      <MetaField
                        label="Job Title"
                        value={
                          selected.job_title ||
                          "Not identified"
                        }
                      />

                      <MetaField
                        label="Email Domain"
                        value={
                          selected.domain ||
                          "Not available"
                        }
                      />

                      <MetaField
                        label="Last Interaction"
                        value={formatDate(
                          selected.last_interaction_at
                        )}
                      />

                    </div>

                  </div>


                  <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4 lg:p-6">

                    <Metric
                      label="Communication"
                      value={
                        selected.communication_total
                      }
                      description={`${selected.inbound_count} inbound ? ${selected.outbound_count} outbound`}
                    />

                    <Metric
                      label="Pending Commitments"
                      value={
                        selected.pending_commitments
                      }
                      description={`${selected.we_owe_them_pending} we owe ? ${selected.they_owe_us_pending} they owe`}
                    />

                    <Metric
                      label="Active Waits"
                      value={
                        selected.active_waits
                      }
                      description="Current responses or obligations expected from this relationship."
                    />

                    <Metric
                      label="Recorded Decisions"
                      value={
                        selected.decisions
                      }
                      description={`${selected.approved_decisions} approved ? ${selected.rejected_decisions} rejected`}
                    />

                  </div>

                </section>


                {detailLoading ? (

                  <section className="animate-pulse rounded-[26px] border border-slate-200 bg-white p-6 shadow-sm">
                    <div className="h-5 w-48 rounded bg-slate-200" />
                    <div className="mt-5 h-20 rounded-2xl bg-slate-100" />
                    <div className="mt-3 h-20 rounded-2xl bg-slate-100" />
                  </section>

                ) : (

                  <>
                    {/* ========================================
                        COMMUNICATIONS
                    ======================================== */}

                    <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm lg:p-6">

                      <SectionHeader
                        icon={<MessagesSquare size={17} />}
                        title="Recent Communication"
                        description="Observed inbound and outbound messages involving this external email."
                        count={
                          communications.length
                        }
                      />


                      {communications.length === 0 ? (

                        <div className="mt-5 rounded-2xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">
                          No communication history is currently available.
                        </div>

                      ) : (

                        <div className="mt-5 space-y-3">

                          {communications.map(
                            (message) => (
                              <div
                                key={
                                  message.message_id
                                }
                                className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-4 sm:flex-row sm:items-center sm:justify-between"
                              >

                                <div className="min-w-0">

                                  <div className="flex flex-wrap items-center gap-2">

                                    <Badge
                                      className={
                                        message.direction ===
                                        "inbound"
                                          ? "border-sky-200 bg-sky-50 text-sky-700"
                                          : "border-violet-200 bg-violet-50 text-violet-700"
                                      }
                                    >
                                      {formatLabel(
                                        message.direction
                                      )}
                                    </Badge>

                                    <span className="text-xs font-medium text-slate-500">
                                      {formatLabel(
                                        message.platform
                                      )}
                                    </span>

                                  </div>


                                  <p className="mt-2 break-words text-sm font-semibold text-slate-900">
                                    {message.subject ||
                                      "Communication"}
                                  </p>

                                  <p className="mt-1 text-xs text-slate-500">
                                    {formatDate(
                                      message.received_at
                                    )}
                                  </p>

                                </div>


                                {message.open_url && (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      openUrl(
                                        message.open_url
                                      )
                                    }
                                    className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                                  >
                                    <Mail size={14} />
                                    Open Email
                                  </button>
                                )}

                              </div>
                            )
                          )}

                        </div>
                      )}

                    </section>


                    {/* ========================================
                        ACCOUNTABILITY
                    ======================================== */}

                    <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm lg:p-6">

                      <SectionHeader
                        icon={<Handshake size={17} />}
                        title="Commitment Accountability"
                        description="Commitments connected to this relationship from the governed Commitment Ledger."
                        count={
                          commitments.length
                        }
                      />


                      {commitments.length === 0 ? (

                        <div className="mt-5 rounded-2xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">
                          No commitments are linked to this relationship.
                        </div>

                      ) : (

                        <div className="mt-5 space-y-3">

                          {commitments.map(
                            (item) => (
                              <div
                                key={
                                  item.commitment_id
                                }
                                className="rounded-2xl border border-slate-200 p-4"
                              >

                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">

                                  <div className="min-w-0">

                                    <div className="flex flex-wrap items-center gap-2">

                                      <Badge
                                        className={
                                          item.direction ===
                                          "WE_OWE_THEM"
                                            ? "border-amber-200 bg-amber-50 text-amber-700"
                                            : "border-sky-200 bg-sky-50 text-sky-700"
                                        }
                                      >
                                        {item.direction ===
                                        "WE_OWE_THEM"
                                          ? "We Owe Them"
                                          : "They Owe Us"}
                                      </Badge>


                                      <Badge className="border-slate-200 bg-slate-50 text-slate-600">
                                        {formatLabel(
                                          item.status
                                        )}
                                      </Badge>

                                    </div>


                                    <p className="mt-3 break-words text-sm font-semibold text-slate-950">
                                      {item.obligation}
                                    </p>

                                  </div>


                                  <div className="text-right text-xs text-slate-500">
                                    <p>
                                      Due
                                    </p>

                                    <p className="mt-1 font-semibold text-slate-700">
                                      {formatDate(
                                        item.current_due_at
                                      )}
                                    </p>
                                  </div>

                                </div>


                                <div className="mt-4 grid gap-4 border-t border-slate-100 pt-4 sm:grid-cols-3">

                                  <MetaField
                                    label="Owner"
                                    value={
                                      item.owner_email ||
                                      "Not assigned"
                                    }
                                  />

                                  <MetaField
                                    label="Source Status"
                                    value={formatLabel(
                                      item.source_status
                                    )}
                                  />

                                  <MetaField
                                    label="Evidence"
                                    value={formatLabel(
                                      item.evidence
                                        ?.evidence_quality ||
                                      "none"
                                    )}
                                  />

                                </div>

                              </div>
                            )
                          )}

                        </div>
                      )}

                    </section>


                    {/* ========================================
                        WAITING
                    ======================================== */}

                    <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm lg:p-6">

                      <SectionHeader
                        icon={<Clock3 size={17} />}
                        title="Waiting For"
                        description="Active external obligations currently expected from this relationship."
                        count={
                          waitingFor.length
                        }
                      />


                      {waitingFor.length === 0 ? (

                        <div className="mt-5 rounded-2xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">
                          Nothing is currently waiting on this relationship.
                        </div>

                      ) : (

                        <div className="mt-5 space-y-3">

                          {waitingFor.map(
                            (item) => (
                              <div
                                key={
                                  item.waiting_id
                                }
                                className="rounded-2xl border border-violet-200 bg-violet-50/40 p-4"
                              >

                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">

                                  <div className="min-w-0">

                                    <Badge
                                      className={
                                        item.due_state ===
                                        "overdue"
                                          ? "border-rose-200 bg-rose-50 text-rose-700"
                                          : item.due_state ===
                                            "due_today"
                                          ? "border-amber-200 bg-amber-50 text-amber-700"
                                          : "border-violet-200 bg-white text-violet-700"
                                      }
                                    >
                                      <CalendarClock
                                        size={12}
                                        className="mr-1.5"
                                      />

                                      {formatLabel(
                                        item.due_state
                                      )}
                                    </Badge>


                                    <p className="mt-3 break-words text-sm font-semibold text-slate-950">
                                      {item.obligation}
                                    </p>

                                  </div>


                                  <p className="text-xs font-semibold text-slate-600">
                                    {formatDate(
                                      item.current_due_at
                                    )}
                                  </p>

                                </div>


                                <div className="mt-4 grid gap-4 border-t border-violet-100 pt-4 sm:grid-cols-2">

                                  <MetaField
                                    label="Internal Owner"
                                    value={
                                      item.owner_email ||
                                      "Not recorded"
                                    }
                                  />

                                  <MetaField
                                    label="Evidence"
                                    value={formatLabel(
                                      item.evidence
                                        ?.evidence_quality ||
                                      "none"
                                    )}
                                  />

                                </div>

                              </div>
                            )
                          )}

                        </div>
                      )}

                    </section>


                    {/* ========================================
                        DECISIONS
                    ======================================== */}

                    <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm lg:p-6">

                      <SectionHeader
                        icon={<Scale size={17} />}
                        title="Recorded Decisions"
                        description="Final approvals or rejections requested by this external relationship."
                        count={
                          decisions.length
                        }
                      />


                      {decisions.length === 0 ? (

                        <div className="mt-5 rounded-2xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">
                          No final decisions are currently linked to this relationship.
                        </div>

                      ) : (

                        <div className="mt-5 space-y-3">

                          {decisions.map(
                            (item) => (
                              <div
                                key={
                                  item.decision_id
                                }
                                className="rounded-2xl border border-slate-200 p-4"
                              >

                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">

                                  <div className="min-w-0">

                                    <Badge
                                      className={
                                        item.outcome ===
                                        "approved"
                                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                          : "border-rose-200 bg-rose-50 text-rose-700"
                                      }
                                    >
                                      {item.outcome ===
                                      "approved" ? (
                                        <CheckCircle2
                                          size={12}
                                          className="mr-1.5"
                                        />
                                      ) : (
                                        <XCircle
                                          size={12}
                                          className="mr-1.5"
                                        />
                                      )}

                                      {formatLabel(
                                        item.outcome
                                      )}
                                    </Badge>


                                    <p className="mt-3 break-words text-sm font-semibold text-slate-950">
                                      {item.title}
                                    </p>

                                    {item.decision_notes && (
                                      <p className="mt-2 text-sm leading-6 text-slate-600">
                                        {item.decision_notes}
                                      </p>
                                    )}

                                  </div>


                                  <p className="text-xs font-semibold text-slate-600">
                                    {formatDate(
                                      item.decision_at
                                    )}
                                  </p>

                                </div>


                                <div className="mt-4 grid gap-4 border-t border-slate-100 pt-4 sm:grid-cols-2">

                                  <MetaField
                                    label="Decision By"
                                    value={
                                      item.decision_by_email ||
                                      "Actor not recorded"
                                    }
                                  />

                                  <MetaField
                                    label="Request Evidence"
                                    value={formatLabel(
                                      item.request_evidence
                                        ?.evidence_quality ||
                                      "none"
                                    )}
                                  />

                                </div>

                              </div>
                            )
                          )}

                        </div>
                      )}

                    </section>


                    {/* ========================================
                        FOOTER CONTEXT
                    ======================================== */}

                    <section className="rounded-[26px] border border-slate-200 bg-slate-950 p-5 text-white shadow-sm lg:p-6">

                      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">

                        <div className="max-w-2xl">

                          <div className="flex items-center gap-2 text-slate-300">
                            <BriefcaseBusiness size={17} />
                            <span className="text-xs font-semibold uppercase tracking-[0.15em]">
                              Relationship context
                            </span>
                          </div>

                          <p className="mt-3 text-sm leading-6 text-slate-300">
                            One UCH is showing factual communication and accountability associated with
                            <span className="font-semibold text-white">
                              {" "}{selected.email}
                            </span>.
                            Company and role details appear only when a persisted Person record is available.
                          </p>

                        </div>


                        <div className="flex flex-wrap gap-2">

                          {selected.company && (
                            <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200">
                              <Building2 size={14} />
                              {selected.company}
                            </span>
                          )}

                          <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200">
                            <Handshake size={14} />
                            {selected.pending_commitments} pending
                          </span>

                          <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200">
                            <Scale size={14} />
                            {selected.decisions} decisions
                          </span>

                        </div>

                      </div>
                    </section>

                  </>
                )}

              </div>
            )}

          </div>
        </section>

      </div>
    </div>
  );
}
