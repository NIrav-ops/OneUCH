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
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Action Center</h1>
            <p className="mt-1 text-sm text-slate-600">
              Convert communication into owned, due, and completed work.
            </p>
          </div>

          <button
            onClick={fetchData}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-100"
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mb-6 grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Open Actions</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{openCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Completed</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{completedCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Ignored</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{ignoredCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Pending Follow-ups</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{pendingFollowups}</p>
          </div>
        </div>

        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setView("open")}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${
                view === "open"
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"
              }`}
            >
              Open
            </button>
            <button
              onClick={() => setView("completed")}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${
                view === "completed"
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"
              }`}
            >
              Completed
            </button>
            <button
              onClick={() => setView("ignored")}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${
                view === "ignored"
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"
              }`}
            >
              Ignored
            </button>
            <button
              onClick={() => setView("all")}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${
                view === "all"
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"
              }`}
            >
              All
            </button>
          </div>

          <div className="w-full md:max-w-md">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search actions or follow-ups..."
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm outline-none focus:border-slate-500"
            />
          </div>
        </div>

        {loading ? (
          <div className="rounded-2xl bg-white p-6 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
            Loading Action Center...
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Actions</h2>
                <p className="text-sm text-slate-500">
                  Assign, date, and complete work extracted from communication.
                </p>
              </div>

              <div className="divide-y divide-slate-200">
                {filteredActions.length === 0 ? (
                  <div className="px-5 py-8 text-sm text-slate-500">No actions found.</div>
                ) : (
                  filteredActions.map((item) => (
                    <div key={item.id} className="px-5 py-4">
                      <div className="flex flex-col gap-4">
                        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="text-base font-semibold text-slate-900">
                                {item.title}
                              </h3>
                              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                                {item.status}
                              </span>
                            </div>

                            {item.description && (
                              <p className="mt-2 text-sm text-slate-600">
                                {item.description}
                              </p>
                            )}

                            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                              <span className="rounded-full bg-slate-100 px-2 py-1">
                                Priority: {item.priority ?? 0}
                              </span>
                              <span className="rounded-full bg-slate-100 px-2 py-1">
                                Confidence: {item.confidence_score ?? 0}%
                              </span>
                              <span className="rounded-full bg-slate-100 px-2 py-1">
                                Owner: {item.owner_email || "Unassigned"}
                              </span>
                              <span className="rounded-full bg-slate-100 px-2 py-1">
                                Due: {formatDate(item.due_date)}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="grid gap-3 md:grid-cols-2">
                          <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">
                              Assign to teammate
                            </label>
                            <select
                              value={assignedById[item.id] || ""}
                              onChange={(e) =>
                                setAssignedById((prev) => ({
                                  ...prev,
                                  [item.id]: e.target.value,
                                }))
                              }
                              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500"
                            >
                              <option value="">Unassigned</option>
                              {teamMembers.map((member) => (
                                <option key={member.id} value={member.id}>
                                  {member.email} ({member.role})
                                </option>
                              ))}
                            </select>
                          </div>

                          <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">
                              Due date
                            </label>
                            <input
                              type="datetime-local"
                              value={dueDateById[item.id] || ""}
                              onChange={(e) =>
                                setDueDateById((prev) => ({
                                  ...prev,
                                  [item.id]: e.target.value,
                                }))
                              }
                              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500"
                            />
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => saveAction(item.id)}
                            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                          >
                            Save Changes
                          </button>

                          {item.status !== "completed" && (
                            <button
                              onClick={() => completeAction(item.id)}
                              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
                            >
                              Complete
                            </button>
                          )}

                          {item.status !== "ignored" && (
                            <button
                              onClick={() => ignoreAction(item.id)}
                              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                            >
                              Ignore
                            </button>
                          )}

                          {item.status !== "open" && (
                            <button
                              onClick={() => reopenAction(item.id)}
                              className="rounded-xl bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600"
                            >
                              Reopen
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Follow-ups</h2>
                <p className="text-sm text-slate-500">
                  Messages waiting for response.
                </p>
              </div>

              <div className="divide-y divide-slate-200">
                {filteredFollowups.length === 0 ? (
                  <div className="px-5 py-8 text-sm text-slate-500">No follow-ups.</div>
                ) : (
                  filteredFollowups.map((item) => (
                    <div key={item.id} className="px-5 py-4">
                      <div className="font-medium text-slate-900">
                        {item.subject || "No Subject"}
                      </div>

                      <div className="mt-1 text-xs text-slate-500">
                        From: {item.sender || "Unknown"}
                      </div>

                      {item.preview && (
                        <div className="mt-2 text-sm text-slate-600">
                          {item.preview}
                        </div>
                      )}

                      <div className="mt-2 text-xs text-slate-500">
                        Due: {formatDate(item.followup_due_at)}
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          onClick={() => navigate(item.open_url || `/inbox?conversation=${item.conversation}`)}
                          className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800"
                        >
                          Open Email
                        </button>

                        <button
                          onClick={() => snoozeFollowup(item.id)}
                          className="rounded-xl bg-indigo-600 px-3 py-2 text-xs font-medium text-white hover:bg-indigo-700"
                        >
                          Remind Tomorrow
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
