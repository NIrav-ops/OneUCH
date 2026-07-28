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
  const [recentActivity, setRecentActivity] = useState([]);

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
      setRecentActivity(
        dashboardRes.data?.recent_activity || []
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

  const escalatedItems = useMemo(() => {
    const escalatedActions = actions.filter(
      (a) => (a.escalation_level || 0) > 0
    );

    const escalatedApprovals = approvals.filter(
      (a) => (a.escalation_level || 0) > 0
    );

    const escalatedFollowups = followups.filter(
      (f) => (f.escalation_level || 0) > 0
    );

    return [
      ...escalatedActions,
      ...escalatedApprovals,
      ...escalatedFollowups,
    ];
  }, [actions, approvals, followups]);

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfTomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);

  const overdueActions = useMemo(() => {
    return openActions.filter((a) => {
      if (!a.due_date) return false;
      const due = new Date(a.due_date);
      return !Number.isNaN(due.getTime()) && due < startOfToday;
    });
  }, [openActions]);

  const dueTodayActions = useMemo(() => {
    return openActions.filter((a) => {
      if (!a.due_date) return false;
      const due = new Date(a.due_date);
      return (
        !Number.isNaN(due.getTime()) &&
        due >= startOfToday &&
        due < startOfTomorrow
      );
    });
  }, [openActions, startOfToday, startOfTomorrow]);

  const topActions = useMemo(() => openActions.slice(0, 5), [openActions]);
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
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
            <p className="mt-1 text-sm text-slate-600">
              A live command view of messages, actions, approvals, and follow-ups.
            </p>
          </div>

          <button
            onClick={fetchData}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-100"
          >
            Refresh
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mb-6 grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Messages</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{messageCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Unread</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{unreadCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Priority</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{priorityCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Open Actions</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{openActions.length}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Due Today</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{dueTodayActions.length}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Overdue</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{overdueActions.length}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">
              Escalated
            </p>

            <p className="mt-2 text-3xl font-semibold text-red-600">
              {escalatedCount}
            </p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">
              Assigned To Me
            </p>

            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {actions.filter(
                a=>a.owner_email
              ).length}
            </p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">
              Pending Approvals
            </p>

            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {pendingApprovals.length}
            </p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">
            Pending Followups
            </p>

            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {pendingFollowups.length}
            </p>
          </div>
          
          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">
              SLA Healthy
            </p>

            <p className="mt-2 text-3xl font-semibold text-green-600">
              {dashboardStats.sla_healthy || 0}
            </p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">
              SLA Warning
            </p>

            <p className="mt-2 text-3xl font-semibold text-yellow-600">
              {dashboardStats.sla_warning || 0}
            </p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">
              SLA Breached
            </p>

            <p className="mt-2 text-3xl font-semibold text-red-600">
              {dashboardStats.sla_breached || 0}
            </p>
          </div>
        </div>
        
        {loading ? (
          <div className="rounded-2xl bg-white p-6 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
            Loading dashboard...
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Overdue Actions</h2>
              </div>

              <div className="divide-y divide-slate-200">
                {overdueActions.length === 0 ? (
                  <div className="px-5 py-8 text-sm text-slate-500">No overdue actions.</div>
                ) : (
                  overdueActions.slice(0, 5).map((item) => (
                    <div key={item.id} className="px-5 py-4">
                      <div className="font-medium text-slate-900">{item.title}</div>
                      <div className="mt-1 text-xs text-rose-600">
                        Due: {formatDate(item.due_date)}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        Owner: {item.owner_email || "Unassigned"}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t border-slate-200 px-5 py-4">
                <button
                  onClick={() => navigate("/actions")}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                  Open Action Center
                </button>
              </div>
            </div>

            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Due Today</h2>
              </div>

              <div className="divide-y divide-slate-200">
                {dueTodayActions.length === 0 ? (
                  <div className="px-5 py-8 text-sm text-slate-500">No actions due today.</div>
                ) : (
                  dueTodayActions.slice(0, 5).map((item) => (
                    <div key={item.id} className="px-5 py-4">
                      <div className="font-medium text-slate-900">{item.title}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        Due: {formatDate(item.due_date)}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        Owner: {item.owner_email || "Unassigned"}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t border-slate-200 px-5 py-4">
                <button
                  onClick={() => navigate("/actions")}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                  Open Action Center
                </button>
              </div>
            </div>

            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Pending Approvals</h2>
              </div>

              <div className="divide-y divide-slate-200">
                {topApprovals.length === 0 ? (
                  <div className="px-5 py-8 text-sm text-slate-500">No pending approvals.</div>
                ) : (
                  topApprovals.map((item) => (
                    <div key={item.id} className="px-5 py-4">
                      <div className="font-medium text-slate-900">{item.title}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        Assigned: {item.assigned_to_email || "Unassigned"}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t border-slate-200 px-5 py-4">
                <button
                  onClick={() => navigate("/approvals")}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                  Open Approval Center
                </button>
              </div>
            </div>

            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Follow-ups</h2>
              </div>

              <div className="divide-y divide-slate-200">
                {topFollowups.length === 0 ? (
                  <div className="px-5 py-8 text-sm text-slate-500">No follow-ups.</div>
                ) : (
                  topFollowups.map((item) => (
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
                          onClick={() =>
                            navigate(item.open_url || `/inbox?conversation=${item.conversation}`)
                          }
                          className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800"
                        >
                          Open Email
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              await axios.post(`/api/actions/followups/${item.id}/snooze/`, {
                                days: 1,
                              });
                              fetchData();
                            } catch (err) {
                              console.error(err);
                              alert("Could not snooze reminder.");
                            }
                          }}
                          className="rounded-xl bg-indigo-600 px-3 py-2 text-xs font-medium text-white hover:bg-indigo-700"
                        >
                          Remind Tomorrow
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t border-slate-200 px-5 py-4">
                <button
                  onClick={() => navigate("/actions")}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                  Open Action Center
                </button>
              </div>
            </div>

            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Priority Messages</h2>
              </div>

              <div className="divide-y divide-slate-200">
                {topPriorityMessages.length === 0 ? (
                  <div className="px-5 py-8 text-sm text-slate-500">
                    No priority messages.
                  </div>
                ) : (
                  topPriorityMessages.map((item) => (
                    <div key={item.id} className="px-5 py-4">
                      <div className="font-medium text-slate-900">
                        {item.subject || "No Subject"}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {item.sender} | {item.platform?.toUpperCase()}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t border-slate-200 px-5 py-4">
                <button
                  onClick={() => navigate("/inbox")}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                  Open Inbox
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}