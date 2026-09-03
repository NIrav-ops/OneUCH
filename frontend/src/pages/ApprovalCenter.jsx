import { useEffect, useMemo, useState } from "react";
import axios from "../axiosConfig";

export default function ApprovalCenter() {
  const [approvals, setApprovals] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [reviewCandidates, setReviewCandidates] = useState([]);
  const [candidateBusyId, setCandidateBusyId] = useState(null);
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

      const [approvalsRes, teamMembersRes, candidatesRes] = await Promise.all([
        axios.get("/api/approvals/"),
        axios.get("/api/approvals/team-members/"),
        axios.get("/api/approvals/review-candidates/"),
      ]);

      const approvalData = Array.isArray(approvalsRes.data) ? approvalsRes.data : [];
      const membersData = Array.isArray(teamMembersRes.data) ? teamMembersRes.data : [];
      const candidateData = Array.isArray(candidatesRes.data)
        ? candidatesRes.data
        : [];

      setApprovals(approvalData);
      setTeamMembers(membersData);
      setReviewCandidates(candidateData);

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


  const reviewCandidate = async (candidateId, decision) => {
    try {
      setCandidateBusyId(candidateId);

      await axios.post(
        `/api/approvals/review-candidates/${candidateId}/${decision}/`
      );

      await fetchData();
    } catch (err) {
      console.error("Approval review failed:", err);
      alert(
        err.response?.data?.error ||
          "Could not review the Approval suggestion."
      );
    } finally {
      setCandidateBusyId(null);
    }
  };

  return (
    <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

      <div className="mx-auto max-w-[1500px]">


        {/* ===================================================
            GOVERNANCE HERO
        ==================================================== */}

        <section className="overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 text-white shadow-sm">

          <div className="flex flex-col gap-7 px-6 py-7 lg:flex-row lg:items-end lg:justify-between lg:px-8 lg:py-8">

            <div className="max-w-3xl">

              <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-300">
                Governed decision queue
              </div>

              <h1 className="mt-5 text-3xl font-semibold tracking-tight text-white">
                Approval Center
              </h1>

              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                Review communication-backed requests, capture decision rationale and keep decision ownership explicit.
              </p>


              <div className="mt-5 flex flex-wrap gap-2">

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Explicit decision
                </span>

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Assigned reviewer
                </span>

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Decision notes preserved
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
                : "Refresh decisions"}
            </button>

          </div>

        </section>


        {error && (

          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>

        )}



        {/* ===================================================
            HUMAN REVIEW QUEUE
        ==================================================== */}

        <section className="mt-5 overflow-hidden rounded-[26px] border border-violet-200 bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-violet-100 bg-violet-50/60 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-600">
                  Human review gate
                </p>
                <span className="rounded-full border border-violet-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-violet-700">
                  No automatic authorization
                </span>
              </div>
              <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                Approval suggestions
              </h2>
              <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">
                Deterministic and governed AI suggestions remain outside the Approval queue until a human explicitly promotes or rejects them.
              </p>
            </div>
            <span className="w-fit rounded-full bg-violet-100 px-3 py-1 text-xs font-semibold text-violet-700">
              {reviewCandidates.length} awaiting review
            </span>
          </div>

          {reviewCandidates.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <p className="text-sm font-semibold text-slate-700">
                No Approval suggestions awaiting review
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Governed extraction suggestions will appear here when review routing is enabled.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {reviewCandidates.map((candidate) => {
                const busy = candidateBusyId === candidate.id;

                return (
                  <article key={candidate.id} className="px-5 py-5 sm:px-6">
                    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-violet-700">
                            {candidate.extraction_method === "deterministic" ? "Deterministic review" : "AI review"}
                          </span>
                          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-500">
                            Confidence {candidate.confidence_score ?? 0}%
                          </span>

                          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-600">
                            {candidate.extraction_method === "deterministic"
                              ? "Deterministic"
                              : "AI"}
                          </span>

                          {candidate.source_domain && (
                            <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-500">
                              {candidate.source_domain}
                            </span>
                          )}

                          {(candidate.occurrence_count ?? 1) > 1 && (
                            <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-semibold text-amber-700">
                              {candidate.occurrence_count} occurrences
                            </span>
                          )}
                        </div>

                        <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                          Source message
                        </p>
                        <p className="mt-1 text-xs font-semibold text-slate-600">
                          {candidate.subject || "No Subject"}
                        </p>

                        <h3 className="mt-3 text-base font-semibold tracking-tight text-slate-950">
                          {candidate.title || "Untitled Approval suggestion"}
                        </h3>

                        {candidate.description && (
                          <p className="mt-2 text-sm leading-6 text-slate-600">
                            {candidate.description}
                          </p>
                        )}

                        {candidate.evidence && (
                          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                              Communication evidence
                            </p>
                            <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-slate-600">
                              {candidate.evidence}
                            </p>
                          </div>
                        )}
                      </div>

                      <aside className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                          Why One UCH suggested this
                        </p>
                        <p className="mt-2 text-xs leading-5 text-slate-600">
                          {candidate.reason || "No additional extraction rationale supplied."}
                        </p>

                        {candidate.approver_reference && (
                          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                              Suggested approver reference
                            </p>
                            <p className="mt-1 text-xs font-semibold text-slate-700">
                              {candidate.approver_reference}
                            </p>
                            <p className="mt-1 text-[10px] leading-4 text-slate-400">
                              Not auto-assigned. Reviewer ownership remains explicit after promotion.
                            </p>
                          </div>
                        )}

                        <div className="mt-4 flex flex-col gap-2">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => reviewCandidate(candidate.id, "promote")}
                            className="rounded-xl bg-slate-950 px-3.5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {busy ? "Processing..." : "Add to Approval Queue"}
                          </button>

                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => reviewCandidate(candidate.id, "reject")}
                            className="rounded-xl border border-rose-200 bg-white px-3.5 py-2.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Reject suggestion
                          </button>

                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => window.location.assign(candidate.open_url || "/inbox")}
                            className="rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Open source communication
                          </button>
                        </div>
                      </aside>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* ===================================================
            DECISION KPI CARDS
        ==================================================== */}

        <section className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">

          {[
            {
              label:
                "Pending",
              value:
                pendingCount,
              description:
                "Requests currently waiting for a decision.",
              style:
                "border-amber-200 bg-amber-50/50",
              valueStyle:
                "text-amber-800",
            },
            {
              label:
                "Approved",
              value:
                approvedCount,
              description:
                "Requests explicitly authorized.",
              style:
                "border-emerald-200 bg-emerald-50/50",
              valueStyle:
                "text-emerald-800",
            },
            {
              label:
                "Rejected",
              value:
                rejectedCount,
              description:
                "Requests explicitly declined.",
              style:
                "border-rose-200 bg-rose-50/50",
              valueStyle:
                "text-rose-800",
            },
            {
              label:
                "Ignored",
              value:
                ignoredCount,
              description:
                "Requests explicitly removed from active review.",
              style:
                "border-slate-200 bg-white",
              valueStyle:
                "text-slate-800",
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
            DECISION COVERAGE
        ==================================================== */}

        <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm sm:px-5">

          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

            <div>

              <h2 className="text-sm font-semibold text-slate-900">
                Decision coverage
              </h2>

              <p className="mt-1 text-xs leading-5 text-slate-500">
                Every final state remains reviewable after the active approval queue is cleared.
              </p>

            </div>


            <div className="flex flex-wrap gap-2 text-[10px] font-semibold">

              <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-amber-700">
                Pending {pendingCount}
              </span>

              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-emerald-700">
                Approved {approvedCount}
              </span>

              <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-rose-700">
                Rejected {rejectedCount}
              </span>

              <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-slate-500">
                Ignored {ignoredCount}
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
                  "pending",
                  "Pending",
                ],
                [
                  "approved",
                  "Approved",
                ],
                [
                  "rejected",
                  "Rejected",
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
                placeholder="Search approval, requester or reviewer..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-slate-300 focus:bg-white focus:ring-2 focus:ring-slate-100"
              />

            </div>

          </div>

        </section>


        {/* ===================================================
            APPROVAL QUEUE
        ==================================================== */}

        {loading ? (

          <section className="mt-5 rounded-[26px] border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">

            <div className="mx-auto h-8 w-8 animate-pulse rounded-full bg-slate-200" />

            <p className="mt-4 text-sm font-medium text-slate-500">
              Loading approval queue...
            </p>

          </section>

        ) : (

          <section className="mt-5 overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">

              <div>

                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-500">
                  Decision queue
                </p>

                <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                  Approvals
                </h2>

                <p className="mt-1 text-xs text-slate-500">
                  Review, assign and record explicit decisions.
                </p>

              </div>


              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
                {filteredApprovals.length}
              </span>

            </div>


            {filteredApprovals.length ===
            0 ? (

              <div className="px-6 py-16 text-center">

                <p className="text-sm font-semibold text-slate-700">
                  No approvals in this view
                </p>

                <p className="mt-1 text-xs text-slate-400">
                  Change the filter or search to review another decision state.
                </p>

              </div>

            ) : (

              <div className="divide-y divide-slate-100">

                {filteredApprovals.map(
                  (item) => {

                    const pending =
                      item.status ===
                      "pending";


                    return (

                      <article
                        key={
                          item.id
                        }
                        className="px-5 py-5 sm:px-6"
                      >

                        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">


                          {/* ===============================
                              DECISION CONTEXT
                          ================================ */}

                          <div className="min-w-0">

                            <div className="flex flex-wrap items-center gap-2">

                              <span
                                className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                                  item.status ===
                                  "approved"
                                    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                    : item.status ===
                                      "rejected"
                                    ? "border-rose-200 bg-rose-50 text-rose-700"
                                    : item.status ===
                                      "ignored"
                                    ? "border-slate-200 bg-slate-50 text-slate-500"
                                    : "border-amber-200 bg-amber-50 text-amber-700"
                                }`}
                              >
                                {item.status ||
                                  "pending"}
                              </span>


                              <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-500">
                                Confidence {item.confidence_score ?? 0}%
                              </span>

                            </div>


                            <h3 className="mt-3 text-lg font-semibold tracking-tight text-slate-950">
                              {item.title ||
                                "Untitled approval"}
                            </h3>


                            {item.description && (

                              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                                {item.description}
                              </p>

                            )}


                            <div className="mt-4 grid gap-3 rounded-2xl border border-slate-100 bg-slate-50/70 p-4 sm:grid-cols-2 lg:grid-cols-4">

                              <div>

                                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Requested by
                                </p>

                                <p className="mt-1 break-words text-xs font-semibold text-slate-700">
                                  {item.requested_by ||
                                    "Unknown"}
                                </p>

                              </div>


                              <div>

                                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Assigned reviewer
                                </p>

                                <p className="mt-1 break-words text-xs font-semibold text-slate-700">
                                  {item.assigned_to_email ||
                                    "Unassigned"}
                                </p>

                              </div>


                              <div>

                                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Due
                                </p>

                                <p className="mt-1 text-xs font-semibold text-slate-700">
                                  {formatDate(
                                    item.due_date
                                  )}
                                </p>

                              </div>


                              <div>

                                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                  Confidence
                                </p>

                                <p className="mt-1 text-xs font-semibold text-slate-700">
                                  {item.confidence_score ?? 0}%
                                </p>

                              </div>

                            </div>


                            {/* =============================
                                REVIEWER ASSIGNMENT
                            ============================== */}

                            <div className="mt-5">

                              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                                Assign reviewer
                              </label>


                              <div className="flex flex-col gap-2 sm:flex-row">

                                <select
                                  value={
                                    assignedById[
                                      item.id
                                    ] ??
                                    item.assigned_to ??
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
                                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs text-slate-700 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100 sm:max-w-sm"
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


                                <button
                                  type="button"
                                  onClick={() =>
                                    handleAssign(
                                      item.id
                                    )
                                  }
                                  className="rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                                >
                                  Assign & Notify
                                </button>

                              </div>

                            </div>


                            {/* =============================
                                DECISION CONTROLS
                            ============================== */}

                            <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4">

                              {pending ? (

                                <>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      handleAction(
                                        item.id,
                                        "approve"
                                      )
                                    }
                                    className="rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700"
                                  >
                                    Approve
                                  </button>


                                  <button
                                    type="button"
                                    onClick={() =>
                                      handleAction(
                                        item.id,
                                        "reject"
                                      )
                                    }
                                    className="rounded-xl bg-rose-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-rose-700"
                                  >
                                    Reject
                                  </button>


                                  <button
                                    type="button"
                                    onClick={() =>
                                      handleAction(
                                        item.id,
                                        "needs-info"
                                      )
                                    }
                                    className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-100"
                                  >
                                    Needs Info
                                  </button>


                                  <button
                                    type="button"
                                    onClick={() =>
                                      handleAction(
                                        item.id,
                                        "ignore"
                                      )
                                    }
                                    className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                                  >
                                    Ignore
                                  </button>
                                </>

                              ) : (

                                <button
                                  type="button"
                                  onClick={() =>
                                    handleAction(
                                      item.id,
                                      "reopen"
                                    )
                                  }
                                  className="rounded-xl bg-slate-950 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
                                >
                                  Reopen
                                </button>

                              )}

                            </div>

                          </div>


                          {/* ===============================
                              DECISION NOTES PANEL
                          ================================ */}

                          <aside className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 sm:p-5">

                            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                              Decision rationale
                            </p>

                            <p className="mt-1 text-xs leading-5 text-slate-500">
                              Capture the reviewer context that should remain with the decision.
                            </p>


                            <textarea
                              value={
                                notesById[
                                  item.id
                                ] ??
                                item.decision_notes ??
                                ""
                              }
                              onChange={(event) =>
                                setNotesById(
                                  (current) => ({
                                    ...current,
                                    [item.id]:
                                      event.target.value,
                                  })
                                )
                              }
                              rows={7}
                              placeholder="Add decision notes..."
                              className="mt-4 w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
                            />


                            {item.decision_notes && (

                              <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3">

                                <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                                  Persisted note
                                </p>

                                <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-slate-600">
                                  {item.decision_notes}
                                </p>

                              </div>

                            )}

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
