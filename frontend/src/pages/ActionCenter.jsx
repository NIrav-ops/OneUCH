import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "../axiosConfig";

export default function ActionCenter() {
  const navigate = useNavigate();

  const [actions, setActions] = useState([]);
  const [followups, setFollowups] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [view, setView] = useState("open"); // open | completed | ignored | all

  const [assignedById, setAssignedById] = useState({});
  const [dueDateById, setDueDateById] = useState({});

  const fetchData = async () => {
    try {
      setError("");
      setRefreshing(true);

      const [actionsRes, followupsRes, teamRes] = await Promise.all([
        axios.get("/api/actions/"),
        axios.get("/api/actions/followups/"),
        axios.get("/api/actions/team-members/"),
      ]);

      const actionData = Array.isArray(actionsRes.data) ? actionsRes.data : [];
      const followupData = Array.isArray(followupsRes.data) ? followupsRes.data : [];
      const teamData = Array.isArray(teamRes.data) ? teamRes.data : [];

      setActions(actionData);
      setFollowups(followupData);
      setTeamMembers(teamData);

      const initialAssigned = {};
      const initialDueDates = {};

      actionData.forEach((item) => {
        initialAssigned[item.id] = item.owner || "";
        initialDueDates[item.id] = item.due_date ? String(item.due_date).slice(0, 16) : "";
      });

      setAssignedById(initialAssigned);
      setDueDateById(initialDueDates);
    } catch (err) {
      console.error("Action Center load error:", err);
      setError("Unable to load Action Center data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredActions = useMemo(() => {
    const q = search.trim().toLowerCase();

    return actions.filter((item) => {
      const matchesSearch =
        !q ||
        (item.title || "").toLowerCase().includes(q) ||
        (item.description || "").toLowerCase().includes(q) ||
        (item.owner_email || "").toLowerCase().includes(q);

      const matchesView =
        view === "all" ||
        (view === "open" && item.status === "open") ||
        (view === "completed" && item.status === "completed") ||
        (view === "ignored" && item.status === "ignored");

      return matchesSearch && matchesView;
    });
  }, [actions, search, view]);

  const filteredFollowups = useMemo(() => {
    const q = search.trim().toLowerCase();

    return followups.filter((item) => {
      const matchesSearch =
        !q ||
        (item.subject || "").toLowerCase().includes(q) ||
        (item.sender || "").toLowerCase().includes(q) ||
        (item.preview || "").toLowerCase().includes(q);

      return matchesSearch;
    });
  }, [followups, search]);

  const openCount = actions.filter((a) => a.status === "open").length;
  const completedCount = actions.filter((a) => a.status === "completed").length;
  const ignoredCount = actions.filter((a) => a.status === "ignored").length;
  const pendingFollowups = followups.filter((f) => f.status === "pending").length;

  const formatDate = (value) => {
    if (!value) return "No due date";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  };

  const saveAction = async (actionId) => {
    try {
      await axios.post(`/api/actions/${actionId}/update/`, {
        assigned_to: assignedById[actionId] || "",
        due_date: dueDateById[actionId] || "",
      });

      await fetchData();
    } catch (err) {
      console.error("Save action failed:", err);
      alert("Could not save action.");
    }
  };

  const completeAction = async (actionId) => {
    try {
      await axios.post(`/api/actions/${actionId}/complete/`);
      await fetchData();
    } catch (err) {
      console.error("Complete failed:", err);
      alert("Could not complete the action.");
    }
  };

  const ignoreAction = async (actionId) => {
    try {
      await axios.post(`/api/actions/${actionId}/ignore/`);
      await fetchData();
    } catch (err) {
      console.error("Ignore failed:", err);
      alert("Could not ignore the action.");
    }
  };

  const reopenAction = async (actionId) => {
    try {
      await axios.post(`/api/actions/${actionId}/reopen/`);
      await fetchData();
    } catch (err) {
      console.error("Reopen failed:", err);
      alert("Could not reopen the action.");
    }
  };

  const snoozeFollowup = async (followupId) => {
    try {
      await axios.post(`/api/actions/followups/${followupId}/snooze/`, {
        days: 1,
      });
      await fetchData();
    } catch (err) {
      console.error("Snooze failed:", err);
      alert("Could not snooze the follow-up.");
    }
  };

  return (
    <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

      <div className="mx-auto max-w-[1540px]">


        {/* ===================================================
            GOVERNED HERO
        ==================================================== */}

        <section className="overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 text-white shadow-sm">

          <div className="flex flex-col gap-7 px-6 py-7 lg:flex-row lg:items-end lg:justify-between lg:px-8 lg:py-8">

            <div className="max-w-3xl">

              <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-300">
                Execution workspace
              </div>

              <h1 className="mt-5 text-3xl font-semibold tracking-tight text-white">
                Action Center
              </h1>

              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                Convert communication into accountable work with explicit ownership,
                deadlines and lifecycle control.
              </p>


              <div className="mt-5 flex flex-wrap gap-2">

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Communication backed
                </span>

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Owner accountable
                </span>

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Deadline governed
                </span>

              </div>

            </div>


            <button
              type="button"
              onClick={
                fetchData
              }
              className="shrink-0 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-100"
            >
              {refreshing
                ? "Refreshing..."
                : "Refresh execution"}
            </button>

          </div>

        </section>


        {error && (

          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>

        )}


        {/* ===================================================
            EXECUTION KPI CARDS
        ==================================================== */}

        <section className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">

          {[
            {
              label:
                "Open actions",
              value:
                openCount,
              description:
                "Work currently requiring execution.",
              style:
                "border-slate-200 bg-white",
              valueStyle:
                "text-slate-950",
            },
            {
              label:
                "Completed",
              value:
                completedCount,
              description:
                "Actions closed through execution.",
              style:
                "border-emerald-200 bg-emerald-50/50",
              valueStyle:
                "text-emerald-800",
            },
            {
              label:
                "Ignored",
              value:
                ignoredCount,
              description:
                "Items explicitly removed from execution.",
              style:
                "border-slate-200 bg-slate-50",
              valueStyle:
                "text-slate-700",
            },
            {
              label:
                "Pending follow-ups",
              value:
                pendingFollowups,
              description:
                "Communication still waiting for response.",
              style:
                "border-violet-200 bg-violet-50/50",
              valueStyle:
                "text-violet-800",
            },
          ].map(
            (metric) => (

              <div
                key={
                  metric.label
                }
                className={`rounded-2xl border p-5 shadow-sm ${metric.style}`}
              >

                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  {metric.label}
                </p>

                <p className={`mt-3 text-3xl font-semibold tracking-tight ${metric.valueStyle}`}>
                  {metric.value}
                </p>

                <p className="mt-2 text-xs leading-5 text-slate-500">
                  {metric.description}
                </p>

              </div>

            )
          )}

        </section>


        {/* ===================================================
            EXECUTION COVERAGE
        ==================================================== */}

        <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm sm:px-5">

          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

            <div>

              <h2 className="text-sm font-semibold text-slate-900">
                Execution coverage
              </h2>

              <p className="mt-1 text-xs leading-5 text-slate-500">
                Work states remain explicit. Completed and ignored items stay available for accountability history.
              </p>

            </div>


            <div className="flex flex-wrap gap-2 text-[10px] font-semibold">

              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-slate-600">
                Open {openCount}
              </span>

              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-emerald-700">
                Completed {completedCount}
              </span>

              <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-slate-500">
                Ignored {ignoredCount}
              </span>

              <span className="rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-violet-700">
                Follow-ups {pendingFollowups}
              </span>

            </div>

          </div>

        </section>


        {/* ===================================================
            FILTER BAR
        ==================================================== */}

        <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">

          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">

            <div className="flex flex-wrap gap-1.5">

              {[
                [
                  "open",
                  "Open",
                ],
                [
                  "completed",
                  "Completed",
                ],
                [
                  "ignored",
                  "Ignored",
                ],
                [
                  "all",
                  "All",
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
                    onClick={() =>
                      setView(
                        value
                      )
                    }
                    className={`rounded-xl px-3.5 py-2 text-xs font-semibold transition ${
                      view ===
                      value
                        ? "bg-slate-950 text-white shadow-sm"
                        : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    {label}
                  </button>

                )
              )}

            </div>


            <div className="w-full xl:max-w-md">

              <input
                value={
                  search
                }
                onChange={(event) =>
                  setSearch(
                    event.target.value
                  )
                }
                placeholder="Search action, owner or follow-up..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-slate-300 focus:bg-white focus:ring-2 focus:ring-slate-100"
              />

            </div>

          </div>

        </section>


        {/* ===================================================
            EXECUTION CONTENT
        ==================================================== */}

        {loading ? (

          <section className="mt-5 rounded-[26px] border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">

            <div className="mx-auto h-8 w-8 animate-pulse rounded-full bg-slate-200" />

            <p className="mt-4 text-sm font-medium text-slate-500">
              Loading execution workspace...
            </p>

          </section>

        ) : (

          <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">


            {/* ===============================================
                ACTION QUEUE
            ================================================ */}

            <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">

                <div>

                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-indigo-500">
                    Owned work
                  </p>

                  <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                    Actions
                  </h2>

                  <p className="mt-1 text-xs text-slate-500">
                    Assign, schedule and progress communication-backed work.
                  </p>

                </div>


                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
                  {filteredActions.length}
                </span>

              </div>


              {filteredActions.length ===
              0 ? (

                <div className="px-6 py-16 text-center">

                  <p className="text-sm font-semibold text-slate-700">
                    No actions in this view
                  </p>

                  <p className="mt-1 text-xs text-slate-400">
                    Change the filter or search to review other work.
                  </p>

                </div>

              ) : (

                <div className="divide-y divide-slate-100">

                  {filteredActions.map(
                    (item) => {

                      const isCompleted =
                        item.status ===
                        "completed";


                      const isIgnored =
                        item.status ===
                        "ignored";


                      return (

                        <article
                          key={
                            item.id
                          }
                          className="px-5 py-5 sm:px-6"
                        >

                          <div className="flex flex-col gap-5">


                            {/* =============================
                                ACTION IDENTITY
                            ============================== */}

                            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">

                              <div className="min-w-0">

                                <div className="flex flex-wrap items-center gap-2">

                                  <span
                                    className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                                      isCompleted
                                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                        : isIgnored
                                        ? "border-slate-200 bg-slate-50 text-slate-500"
                                        : "border-indigo-200 bg-indigo-50 text-indigo-700"
                                    }`}
                                  >
                                    {item.status ||
                                      "open"}
                                  </span>


                                  <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-500">
                                    Priority {item.priority ?? 0}
                                  </span>


                                  <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-500">
                                    Confidence {item.confidence_score ?? 0}%
                                  </span>

                                </div>


                                <h3 className="mt-3 text-base font-semibold tracking-tight text-slate-950">
                                  {item.title ||
                                    "Untitled action"}
                                </h3>


                                {item.description && (

                                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                                    {item.description}
                                  </p>

                                )}

                              </div>

                            </div>


                            {/* =============================
                                ACCOUNTABILITY CONTEXT
                            ============================== */}

                            <div className="grid gap-3 rounded-2xl border border-slate-100 bg-slate-50/70 p-4 sm:grid-cols-2">

                              <div>

                                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Current owner
                                </p>

                                <p className="mt-1 text-xs font-semibold text-slate-700">
                                  {item.owner_email ||
                                    "Unassigned"}
                                </p>

                              </div>


                              <div>

                                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Current due date
                                </p>

                                <p className="mt-1 text-xs font-semibold text-slate-700">
                                  {formatDate(
                                    item.due_date
                                  )}
                                </p>

                              </div>

                            </div>


                            {/* =============================
                                EDIT EXECUTION
                            ============================== */}

                            <div className="grid gap-3 sm:grid-cols-2">

                              <div>

                                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Assign owner
                                </label>

                                <select
                                  value={
                                    assignedById[
                                      item.id
                                    ] ||
                                    ""
                                  }
                                  onChange={(event) =>
                                    setAssignedById(
                                      (current) => ({
                                        ...current,
                                        [item.id]:
                                          event.target.value,
                                      })
                                    )
                                  }
                                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs text-slate-700 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
                                >

                                  <option value="">
                                    Unassigned
                                  </option>


                                  {teamMembers.map(
                                    (member) => (

                                      <option
                                        key={
                                          member.id
                                        }
                                        value={
                                          member.id
                                        }
                                      >
                                        {member.email} ({member.role})
                                      </option>

                                    )
                                  )}

                                </select>

                              </div>


                              <div>

                                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Due date
                                </label>

                                <input
                                  type="datetime-local"
                                  value={
                                    dueDateById[
                                      item.id
                                    ] ||
                                    ""
                                  }
                                  onChange={(event) =>
                                    setDueDateById(
                                      (current) => ({
                                        ...current,
                                        [item.id]:
                                          event.target.value,
                                      })
                                    )
                                  }
                                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs text-slate-700 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
                                />

                              </div>

                            </div>


                            {/* =============================
                                ACTION CONTROLS
                            ============================== */}

                            <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">

                              <button
                                type="button"
                                onClick={() =>
                                  saveAction(
                                    item.id
                                  )
                                }
                                className="rounded-xl bg-slate-950 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
                              >
                                Save changes
                              </button>


                              {!isCompleted && (

                                <button
                                  type="button"
                                  onClick={() =>
                                    completeAction(
                                      item.id
                                    )
                                  }
                                  className="rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                                >
                                  Complete
                                </button>

                              )}


                              {!isIgnored && (

                                <button
                                  type="button"
                                  onClick={() =>
                                    ignoreAction(
                                      item.id
                                    )
                                  }
                                  className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                                >
                                  Ignore
                                </button>

                              )}


                              {item.status !==
                                "open" && (

                                <button
                                  type="button"
                                  onClick={() =>
                                    reopenAction(
                                      item.id
                                    )
                                  }
                                  className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-100"
                                >
                                  Reopen
                                </button>

                              )}

                            </div>

                          </div>

                        </article>

                      );

                    }
                  )}

                </div>

              )}

            </section>


            {/* ===============================================
                FOLLOW-UP RAIL
            ================================================ */}

            <aside className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

              <div className="border-b border-slate-100 px-5 py-4">

                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-500">
                  External response
                </p>

                <div className="mt-1 flex items-center justify-between gap-3">

                  <h2 className="text-base font-semibold text-slate-950">
                    Follow-ups
                  </h2>

                  <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
                    {filteredFollowups.length}
                  </span>

                </div>

                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Communication currently waiting for a response.
                </p>

              </div>


              {filteredFollowups.length ===
              0 ? (

                <div className="px-5 py-12 text-center">

                  <p className="text-sm font-medium text-slate-600">
                    No follow-ups
                  </p>

                  <p className="mt-1 text-xs text-slate-400">
                    Nothing currently matches this search.
                  </p>

                </div>

              ) : (

                <div className="divide-y divide-slate-100">

                  {filteredFollowups.map(
                    (item) => (

                      <article
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


                        {item.preview && (

                          <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-500">
                            {item.preview}
                          </p>

                        )}


                        <div className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-[10px] text-slate-500">

                          Expected response{" "}

                          <span className="font-semibold text-slate-700">
                            {formatDate(
                              item.followup_due_at
                            )}
                          </span>

                        </div>


                        <div className="mt-3 flex flex-wrap gap-2">

                          <button
                            type="button"
                            onClick={() =>
                              navigate(
                                item.open_url ||
                                `/inbox?conversation=${item.conversation}`
                              )
                            }
                            className="rounded-lg bg-slate-950 px-2.5 py-1.5 text-[10px] font-semibold text-white hover:bg-slate-800"
                          >
                            Open email
                          </button>


                          <button
                            type="button"
                            onClick={() =>
                              snoozeFollowup(
                                item.id
                              )
                            }
                            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50"
                          >
                            Remind tomorrow
                          </button>

                        </div>

                      </article>

                    )
                  )}

                </div>

              )}

            </aside>

          </div>

        )}

      </div>

    </div>
  );
}
