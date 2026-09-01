import { useEffect, useMemo, useState } from "react";
import axios from "../axiosConfig";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [actions, setActions] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [followups, setFollowups] = useState([]);
  const [priorityMessages, setPriorityMessages] = useState([]);

  const [messageCount, setMessageCount] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [priorityCount, setPriorityCount] = useState(0);
  const [escalatedCount, setEscalatedCount] = useState(0);
  const [dashboardStats, setDashboardStats] = useState({});

  const fetchData = async () => {
    try {
      setError("");

      const [
        actionsRes,
        approvalsRes,
        followupsRes,
        inboxRes,
        unreadRes,
        priorityRes,
        dashboardRes,
      ] = await Promise.all([
        axios.get("/api/actions/"),
        axios.get("/api/approvals/"),
        axios.get("/api/actions/followups/"),
        axios.get("/api/inbox/unified/?page=1"),
        axios.get("/api/inbox/unified/?unread=true&page=1"),
        axios.get("/api/inbox/unified/?priority=true&page=1"),
        axios.get("/api/dashboard/"),
      ]);

      setActions(Array.isArray(actionsRes.data) ? actionsRes.data : []);
      setApprovals(Array.isArray(approvalsRes.data) ? approvalsRes.data : []);
      setFollowups(Array.isArray(followupsRes.data) ? followupsRes.data : []);
      setPriorityMessages(priorityRes.data?.results || []);

      setMessageCount(inboxRes.data?.count || 0);
      setUnreadCount(unreadRes.data?.count || 0);
      setPriorityCount(priorityRes.data?.count || 0);

      const escalatedActions =
        (actionsRes.data || []).filter(
          (a) => (a.escalation_level || 0) > 0
        ).length;

      const escalatedApprovals =
        (approvalsRes.data || []).filter(
          (a) => (a.escalation_level || 0) > 0
        ).length;

      const escalatedFollowups =
        (followupsRes.data || []).filter(
          (f) => (f.escalation_level || 0) > 0
        ).length;

      setEscalatedCount(
        escalatedActions +
        escalatedApprovals +
        escalatedFollowups
      );

      setDashboardStats(
        dashboardRes.data || {}
      );
      
    } catch (err) {
      console.error("Dashboard load error:", err);
      setError("Unable to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openActions = useMemo(
    () => actions.filter((a) => a.status === "open"),
    [actions]
  );

  const pendingApprovals = useMemo(
    () => approvals.filter((a) => a.status === "pending"),
    [approvals]
  );

  const pendingFollowups = useMemo(
    () => followups.filter((f) => f.status === "pending"),
    [followups]
  );

  const overdueActions = useMemo(() => {
    const now = new Date();

    const startOfToday = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate()
    );

    return openActions.filter((a) => {
      if (!a.due_date) return false;

      const due = new Date(a.due_date);

      return (
        !Number.isNaN(due.getTime()) &&
        due < startOfToday
      );
    });
  }, [openActions]);

  const dueTodayActions = useMemo(() => {
    const now = new Date();

    const startOfToday = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate()
    );

    const startOfTomorrow = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() + 1
    );

    return openActions.filter((a) => {
      if (!a.due_date) return false;

      const due = new Date(a.due_date);

      return (
        !Number.isNaN(due.getTime()) &&
        due >= startOfToday &&
        due < startOfTomorrow
      );
    });
  }, [openActions]);

  const topApprovals = useMemo(() => pendingApprovals.slice(0, 5), [pendingApprovals]);
  const topFollowups = useMemo(() => pendingFollowups.slice(0, 5), [pendingFollowups]);
  const topPriorityMessages = useMemo(() => priorityMessages.slice(0, 5), [priorityMessages]);

  const formatDate = (value) => {
    if (!value) return "No due date";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  };

  return (
    <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

      <div className="mx-auto max-w-[1600px]">

        {/* ===================================================
            COMMAND HEADER
        ==================================================== */}

        <section className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm">

          <div className="flex flex-col gap-5 border-b border-slate-100 px-5 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-7">

            <div className="max-w-3xl">

              <div className="mb-2 flex items-center gap-2">

                <span className="h-2 w-2 rounded-full bg-emerald-500" />

                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                  Live execution pulse
                </span>

              </div>

              <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
                What needs your attention today
              </h1>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                Communication, accountable work, approvals and response obligations in one operational view.
              </p>

            </div>


            <div className="flex flex-wrap gap-2">

              <button
                type="button"
                onClick={() =>
                  navigate(
                    "/attention"
                  )
                }
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
              >
                Attention Center
              </button>

              <button
                type="button"
                onClick={fetchData}
                className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
              >
                Refresh workspace
              </button>

            </div>

          </div>


          {error && (

            <div className="mx-5 mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 sm:mx-6 lg:mx-7">
              {error}
            </div>

          )}


          {/* =================================================
              PRIMARY KPIs
          ================================================== */}

          <div className="grid gap-px bg-slate-200 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">

            {[
              {
                label:
                  "Unread",
                value:
                  unreadCount,
                detail:
                  "Messages needing review",
                route:
                  "/inbox",
                tone:
                  "text-sky-700",
              },
              {
                label:
                  "Open actions",
                value:
                  openActions.length,
                detail:
                  "Active owned work",
                route:
                  "/actions",
                tone:
                  "text-indigo-700",
              },
              {
                label:
                  "Due today",
                value:
                  dueTodayActions.length,
                detail:
                  "Requires completion today",
                route:
                  "/my-work",
                tone:
                  "text-amber-700",
              },
              {
                label:
                  "Overdue",
                value:
                  overdueActions.length,
                detail:
                  "Past due boundary",
                route:
                  "/attention",
                tone:
                  "text-rose-700",
              },
              {
                label:
                  "Approvals",
                value:
                  pendingApprovals.length,
                detail:
                  "Waiting for a decision",
                route:
                  "/approvals",
                tone:
                  "text-violet-700",
              },
              {
                label:
                  "Waiting for",
                value:
                  pendingFollowups.length,
                detail:
                  "External responses due",
                route:
                  "/waiting-for",
                tone:
                  "text-emerald-700",
              },
            ].map(
              (metric) => (

                <button
                  type="button"
                  key={
                    metric.label
                  }
                  onClick={() =>
                    navigate(
                      metric.route
                    )
                  }
                  className="bg-white px-5 py-5 text-left transition hover:bg-slate-50"
                >

                  <p className="text-xs font-semibold text-slate-500">
                    {metric.label}
                  </p>

                  <p className={`mt-2 text-3xl font-semibold tracking-tight ${metric.tone}`}>
                    {metric.value}
                  </p>

                  <p className="mt-1 text-[11px] leading-4 text-slate-400">
                    {metric.detail}
                  </p>

                </button>

              )
            )}

          </div>

        </section>


        {/* ===================================================
            SECONDARY HEALTH
        ==================================================== */}

        <section className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">

          {[
            [
              "Messages",
              messageCount,
            ],
            [
              "Priority",
              priorityCount,
            ],
            [
              "Escalated",
              escalatedCount,
            ],
            [
              "Assigned",
              actions.filter(
                (item) =>
                  item.owner_email
              ).length,
            ],
            [
              "SLA healthy",
              dashboardStats.sla_healthy ||
              0,
            ],
            [
              "SLA warning",
              dashboardStats.sla_warning ||
              0,
            ],
            [
              "SLA breached",
              dashboardStats.sla_breached ||
              0,
            ],
          ].map(
            (
              [
                label,
                value,
              ]
            ) => (

              <div
                key={
                  label
                }
                className="rounded-2xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm"
              >

                <p className="text-[11px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                  {label}
                </p>

                <p
                  className={`mt-1.5 text-xl font-semibold ${
                    label ===
                    "SLA breached"
                      ? "text-rose-700"
                      : label ===
                        "SLA warning"
                      ? "text-amber-700"
                      : label ===
                        "SLA healthy"
                      ? "text-emerald-700"
                      : "text-slate-900"
                  }`}
                >
                  {value}
                </p>

              </div>

            )
          )}

        </section>


        {loading ? (

          <section className="mt-6 rounded-[26px] border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">

            <div className="mx-auto h-8 w-8 animate-pulse rounded-full bg-slate-200" />

            <p className="mt-4 text-sm font-medium text-slate-600">
              Building your execution view...
            </p>

          </section>

        ) : (

          <>
            {/* ===============================================
                ATTENTION QUEUES
            ================================================ */}

            <div className="mt-6 grid gap-6 xl:grid-cols-2">

              <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

                <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">

                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-rose-500">
                      Intervention
                    </p>

                    <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                      Overdue actions
                    </h2>
                  </div>

                  <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">
                    {overdueActions.length}
                  </span>

                </div>


                <div className="divide-y divide-slate-100">

                  {overdueActions.length ===
                  0 ? (

                    <div className="px-6 py-12 text-center">

                      <p className="text-sm font-medium text-slate-700">
                        No overdue actions
                      </p>

                      <p className="mt-1 text-xs text-slate-400">
                        Nothing currently requires overdue intervention.
                      </p>

                    </div>

                  ) : (

                    overdueActions
                      .slice(
                        0,
                        5
                      )
                      .map(
                        (item) => (

                          <div
                            key={
                              item.id
                            }
                            className="px-5 py-4 sm:px-6"
                          >

                            <div className="flex gap-3">

                              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-rose-500" />

                              <div className="min-w-0 flex-1">

                                <p className="truncate text-sm font-semibold text-slate-900">
                                  {item.title}
                                </p>

                                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">

                                  <span>
                                    Due{" "}
                                    <span className="font-semibold text-rose-700">
                                      {formatDate(
                                        item.due_date
                                      )}
                                    </span>
                                  </span>

                                  <span>
                                    Owner{" "}
                                    <span className="font-medium text-slate-700">
                                      {item.owner_email ||
                                        "Unassigned"}
                                    </span>
                                  </span>

                                </div>

                              </div>

                            </div>

                          </div>

                        )
                      )
                  )}

                </div>


                <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-3.5 sm:px-6">

                  <button
                    type="button"
                    onClick={() =>
                      navigate(
                        "/actions"
                      )
                    }
                    className="text-sm font-semibold text-slate-700 hover:text-slate-950"
                  >
                    View all actions ?
                  </button>

                </div>

              </section>


              <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

                <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">

                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-amber-500">
                      Today's execution
                    </p>

                    <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                      Due today
                    </h2>
                  </div>

                  <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                    {dueTodayActions.length}
                  </span>

                </div>


                <div className="divide-y divide-slate-100">

                  {dueTodayActions.length ===
                  0 ? (

                    <div className="px-6 py-12 text-center">

                      <p className="text-sm font-medium text-slate-700">
                        No actions due today
                      </p>

                      <p className="mt-1 text-xs text-slate-400">
                        Your current action queue has no due-today items.
                      </p>

                    </div>

                  ) : (

                    dueTodayActions
                      .slice(
                        0,
                        5
                      )
                      .map(
                        (item) => (

                          <div
                            key={
                              item.id
                            }
                            className="px-5 py-4 sm:px-6"
                          >

                            <p className="text-sm font-semibold text-slate-900">
                              {item.title}
                            </p>

                            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">

                              <span>
                                {formatDate(
                                  item.due_date
                                )}
                              </span>

                              <span>
                                {item.owner_email ||
                                  "Unassigned"}
                              </span>

                            </div>

                          </div>

                        )
                      )
                  )}

                </div>


                <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-3.5 sm:px-6">

                  <button
                    type="button"
                    onClick={() =>
                      navigate(
                        "/my-work"
                      )
                    }
                    className="text-sm font-semibold text-slate-700 hover:text-slate-950"
                  >
                    Open My Work ?
                  </button>

                </div>

              </section>

            </div>


            {/* ===============================================
                DECISION / RESPONSE / COMMUNICATION
            ================================================ */}

            <div className="mt-6 grid gap-6 lg:grid-cols-3">

              <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

                <div className="border-b border-slate-100 px-5 py-4">

                  <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-violet-500">
                    Governance
                  </p>

                  <div className="mt-1 flex items-center justify-between gap-3">

                    <h2 className="text-base font-semibold text-slate-950">
                      Pending approvals
                    </h2>

                    <span className="text-xs font-semibold text-slate-400">
                      {pendingApprovals.length}
                    </span>

                  </div>

                </div>


                <div className="divide-y divide-slate-100">

                  {topApprovals.length ===
                  0 ? (

                    <div className="px-5 py-10 text-center text-sm text-slate-400">
                      No pending approvals.
                    </div>

                  ) : (

                    topApprovals.map(
                      (item) => (

                        <div
                          key={
                            item.id
                          }
                          className="px-5 py-4"
                        >

                          <p className="line-clamp-2 text-sm font-semibold text-slate-900">
                            {item.title}
                          </p>

                          <p className="mt-1.5 truncate text-xs text-slate-500">
                            {item.assigned_to_email ||
                              "Unassigned"}
                          </p>

                        </div>

                      )
                    )
                  )}

                </div>


                <div className="border-t border-slate-100 px-5 py-3.5">

                  <button
                    type="button"
                    onClick={() =>
                      navigate(
                        "/approvals"
                      )
                    }
                    className="text-xs font-semibold text-slate-700 hover:text-slate-950"
                  >
                    Approval Center ?
                  </button>

                </div>

              </section>


              <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

                <div className="border-b border-slate-100 px-5 py-4">

                  <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-emerald-500">
                    External response
                  </p>

                  <div className="mt-1 flex items-center justify-between gap-3">

                    <h2 className="text-base font-semibold text-slate-950">
                      Follow-ups
                    </h2>

                    <span className="text-xs font-semibold text-slate-400">
                      {pendingFollowups.length}
                    </span>

                  </div>

                </div>


                <div className="divide-y divide-slate-100">

                  {topFollowups.length ===
                  0 ? (

                    <div className="px-5 py-10 text-center text-sm text-slate-400">
                      No pending follow-ups.
                    </div>

                  ) : (

                    topFollowups.map(
                      (item) => (

                        <div
                          key={
                            item.id
                          }
                          className="px-5 py-4"
                        >

                          <p className="line-clamp-2 text-sm font-semibold text-slate-900">
                            {item.subject ||
                              "No Subject"}
                          </p>

                          <p className="mt-1 truncate text-xs text-slate-500">
                            {item.sender ||
                              "Unknown sender"}
                          </p>

                          <div className="mt-3 flex flex-wrap gap-2">

                            <button
                              type="button"
                              onClick={() =>
                                navigate(
                                  item.open_url ||
                                  `/inbox?conversation=${item.conversation}`
                                )
                              }
                              className="rounded-lg bg-slate-950 px-2.5 py-1.5 text-[11px] font-semibold text-white hover:bg-slate-800"
                            >
                              Open
                            </button>

                            <button
                              type="button"
                              onClick={
                                async () => {

                                  try {

                                    await axios.post(
                                      `/api/actions/followups/${item.id}/snooze/`,
                                      {
                                        days:
                                          1,
                                      }
                                    );

                                    fetchData();

                                  } catch (err) {

                                    console.error(
                                      err
                                    );

                                    setError(
                                      "Could not snooze reminder."
                                    );

                                  }

                                }
                              }
                              className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-50"
                            >
                              Tomorrow
                            </button>

                          </div>

                        </div>

                      )
                    )
                  )}

                </div>


                <div className="border-t border-slate-100 px-5 py-3.5">

                  <button
                    type="button"
                    onClick={() =>
                      navigate(
                        "/waiting-for"
                      )
                    }
                    className="text-xs font-semibold text-slate-700 hover:text-slate-950"
                  >
                    Waiting For ?
                  </button>

                </div>

              </section>


              <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

                <div className="border-b border-slate-100 px-5 py-4">

                  <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-sky-500">
                    Communication
                  </p>

                  <div className="mt-1 flex items-center justify-between gap-3">

                    <h2 className="text-base font-semibold text-slate-950">
                      Priority messages
                    </h2>

                    <span className="text-xs font-semibold text-slate-400">
                      {priorityCount}
                    </span>

                  </div>

                </div>


                <div className="divide-y divide-slate-100">

                  {topPriorityMessages.length ===
                  0 ? (

                    <div className="px-5 py-10 text-center text-sm text-slate-400">
                      No priority messages.
                    </div>

                  ) : (

                    topPriorityMessages.map(
                      (item) => (

                        <div
                          key={
                            item.id
                          }
                          className="px-5 py-4"
                        >

                          <p className="line-clamp-2 text-sm font-semibold text-slate-900">
                            {item.subject ||
                              "No Subject"}
                          </p>

                          <div className="mt-1.5 flex items-center justify-between gap-2 text-xs text-slate-500">

                            <span className="truncate">
                              {item.sender ||
                                "Unknown sender"}
                            </span>

                            <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-500">
                              {item.platform ||
                                "mail"}
                            </span>

                          </div>

                        </div>

                      )
                    )
                  )}

                </div>


                <div className="border-t border-slate-100 px-5 py-3.5">

                  <button
                    type="button"
                    onClick={() =>
                      navigate(
                        "/inbox"
                      )
                    }
                    className="text-xs font-semibold text-slate-700 hover:text-slate-950"
                  >
                    Unified Inbox ?
                  </button>

                </div>

              </section>

            </div>

          </>

        )}

      </div>

    </div>
  );
}
