import { useEffect, useMemo, useState } from "react";
import axios from "../axiosConfig";

export default function ApprovalCenter() {
  const [approvals, setApprovals] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [view, setView] = useState("pending"); // pending | approved | rejected | ignored | all
  const [notesById, setNotesById] = useState({});
  const [assignedById, setAssignedById] = useState({});

  const fetchData = async () => {
    try {
      setError("");
      setRefreshing(true);

      const [approvalsRes, teamMembersRes] = await Promise.all([
        axios.get("/api/approvals/"),
        axios.get("/api/approvals/team-members/"),
      ]);

      const approvalData = Array.isArray(approvalsRes.data) ? approvalsRes.data : [];
      const membersData = Array.isArray(teamMembersRes.data) ? teamMembersRes.data : [];

      setApprovals(approvalData);
      setTeamMembers(membersData);

      const initialNotes = {};
      const initialAssigned = {};

      approvalData.forEach((item) => {
        initialNotes[item.id] = item.decision_notes || "";
        initialAssigned[item.id] = item.assigned_to || "";
      });

      setNotesById(initialNotes);
      setAssignedById(initialAssigned);
    } catch (err) {
      console.error(err);
      setError("Unable to load approvals.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAction = async (approvalId, actionType) => {
    try {
      const notes = notesById[approvalId] || "";

      await axios.post(
        `/api/approvals/${approvalId}/${actionType}/`,
        { decision_notes: notes }
      );

      await fetchData();
    } catch (err) {
      console.error(err);
      alert("Action failed.");
    }
  };

  const handleAssign = async (approvalId) => {
    try {
      await axios.post(`/api/approvals/${approvalId}/assign/`, {
        assigned_to: assignedById[approvalId] || null,
      });

      await fetchData();
    } catch (err) {
      console.error(err);
      alert("Assignment failed.");
    }
  };

  const filteredApprovals = useMemo(() => {
    const q = search.trim().toLowerCase();

    return approvals.filter((item) => {
      const matchesSearch =
        !q ||
        (item.title || "").toLowerCase().includes(q) ||
        (item.description || "").toLowerCase().includes(q) ||
        (item.requested_by || "").toLowerCase().includes(q) ||
        (item.decision_notes || "").toLowerCase().includes(q) ||
        (item.assigned_to_email || "").toLowerCase().includes(q);

      const matchesView =
        view === "all" ||
        (view === "pending" && item.status === "pending") ||
        (view === "approved" && item.status === "approved") ||
        (view === "rejected" && item.status === "rejected") ||
        (view === "ignored" && item.status === "ignored");

      return matchesSearch && matchesView;
    });
  }, [approvals, search, view]);

  const pendingCount = approvals.filter((a) => a.status === "pending").length;
  const approvedCount = approvals.filter((a) => a.status === "approved").length;
  const rejectedCount = approvals.filter((a) => a.status === "rejected").length;
  const ignoredCount = approvals.filter((a) => a.status === "ignored").length;

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
            <h1 className="text-2xl font-semibold text-slate-900">Approval Center</h1>
            <p className="mt-1 text-sm text-slate-600">
              Requests that need approval, rejection, clarification, assignment, or follow-through.
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
            <p className="text-sm text-slate-500">Pending Approvals</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{pendingCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Approved</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{approvedCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Rejected</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{rejectedCount}</p>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm text-slate-500">Ignored</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{ignoredCount}</p>
          </div>
        </div>

        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setView("pending")}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${
                view === "pending"
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"
              }`}
            >
              Pending
            </button>

            <button
              onClick={() => setView("approved")}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${
                view === "approved"
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"
              }`}
            >
              Approved
            </button>

            <button
              onClick={() => setView("rejected")}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${
                view === "rejected"
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"
              }`}
            >
              Rejected
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
              placeholder="Search approvals..."
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm outline-none focus:border-slate-500"
            />
          </div>
        </div>

        {loading ? (
          <div className="rounded-2xl bg-white p-6 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
            Loading Approval Center...
          </div>
        ) : (
          <div className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-slate-900">Approvals</h2>
              <p className="text-sm text-slate-500">
                Items requiring a decision.
              </p>
            </div>

            <div className="divide-y divide-slate-200">
              {filteredApprovals.length === 0 ? (
                <div className="px-5 py-8 text-sm text-slate-500">
                  No approvals found.
                </div>
              ) : (
                filteredApprovals.map((item) => (
                  <div key={item.id} className="px-5 py-4">
                    <div className="flex flex-col gap-4">
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div className="min-w-0 w-full">
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
                              Requested by: {item.requested_by || "Unknown"}
                            </span>
                            <span className="rounded-full bg-slate-100 px-2 py-1">
                              Confidence: {item.confidence_score ?? 0}%
                            </span>
                            <span className="rounded-full bg-slate-100 px-2 py-1">
                              Due: {formatDate(item.due_date)}
                            </span>
                            <span className="rounded-full bg-slate-100 px-2 py-1">
                              Assigned: {item.assigned_to_email || "Unassigned"}
                            </span>
                          </div>

                          <div className="mt-4">
                            <div className="mb-1 text-sm font-medium text-slate-700">
                              Decision notes
                            </div>
                            <textarea
                              value={notesById[item.id] ?? item.decision_notes ?? ""}
                              onChange={(e) =>
                                setNotesById((prev) => ({
                                  ...prev,
                                  [item.id]: e.target.value,
                                }))
                              }
                              rows={3}
                              placeholder="Add decision notes..."
                              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500"
                            />
                          </div>

                          <div className="mt-4">
                            <div className="mb-1 text-sm font-medium text-slate-700">
                              Assign to teammate
                            </div>
                            <div className="flex flex-col gap-2 md:flex-row md:items-center">
                              <select
                                value={assignedById[item.id] ?? item.assigned_to ?? ""}
                                onChange={(e) =>
                                  setAssignedById((prev) => ({
                                    ...prev,
                                    [item.id]: e.target.value,
                                  }))
                                }
                                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 md:max-w-xs"
                              >
                                <option value="">Unassigned</option>
                                {teamMembers.map((member) => (
                                  <option key={member.id} value={member.id}>
                                    {member.email} ({member.role})
                                  </option>
                                ))}
                              </select>

                              <button
                                onClick={() => handleAssign(item.id)}
                                className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                              >
                                Assign & Notify
                              </button>
                            </div>
                          </div>

                          {item.decision_notes ? (
                            <div className="mt-3 text-xs text-slate-500">
                              Saved notes: {item.decision_notes}
                            </div>
                          ) : null}
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {item.status === "pending" ? (
                          <>
                            <button
                              onClick={() => handleAction(item.id, "approve")}
                              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleAction(item.id, "reject")}
                              className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700"
                            >
                              Reject
                            </button>
                            <button
                              onClick={() => handleAction(item.id, "needs-info")}
                              className="rounded-xl bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600"
                            >
                              Needs Info
                            </button>
                            <button
                              onClick={() => handleAction(item.id, "ignore")}
                              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                            >
                              Ignore
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleAction(item.id, "reopen")}
                            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
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
        )}
      </div>
    </div>
  );
}