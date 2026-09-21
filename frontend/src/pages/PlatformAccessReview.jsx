import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import axios from "../axiosConfig";

const FILTERS = ["pending", "approved", "rejected"];

export default function PlatformAccessReview() {
  const [filter, setFilter] = useState("pending");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const [approvalReady, setApprovalReady] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setMessage("");

    try {
      const [registry, config] = await Promise.all([
        axios.get("/api/auth/platform/registrations/", {
          params: { status: filter, limit: 50 },
        }),
        axios.get("/api/auth/identity/registration/config/"),
      ]);

      setItems(
        Array.isArray(registry.data?.registrations)
          ? registry.data.registrations
          : []
      );
      setApprovalReady(config.data?.approval_email_enabled === true);
      setUnavailable(false);
    } catch (error) {
      if (error.response?.status === 403) {
        setUnavailable(true);
        setItems([]);
      } else {
        setMessage("Unable to load platform access requests.");
      }
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const allowAccess = async (registration) => {
    if (!approvalReady || busyId) return;

    const ok = window.confirm(
      `Allow platform access for ${registration.user.first_name} ${registration.user.last_name}?\n\nThis activates the user and workspace and queues the approval notification.`
    );
    if (!ok) return;

    try {
      setBusyId(registration.registration_id);
      await axios.post(
        `/api/auth/platform/registrations/${registration.registration_id}/approve/`,
        {}
      );
      setMessage("Platform access allowed.");
      await load();
    } catch {
      setMessage("Unable to allow this request.");
    } finally {
      setBusyId("");
    }
  };

  const rejectAccess = async (registration) => {
    if (busyId) return;

    const reason = window.prompt("Internal rejection reason:");
    if (reason === null) return;

    const normalized = reason.trim();
    if (!normalized || normalized.length > 1000) {
      setMessage("A rejection reason is required.");
      return;
    }

    try {
      setBusyId(registration.registration_id);
      await axios.post(
        `/api/auth/platform/registrations/${registration.registration_id}/reject/`,
        { rejection_reason: normalized }
      );
      setMessage("Request rejected. No email was sent.");
      await load();
    } catch {
      setMessage("Unable to reject this request.");
    } finally {
      setBusyId("");
    }
  };

  if (unavailable) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-lg font-semibold text-slate-950">Page unavailable</h1>
          <p className="mt-2 text-sm text-slate-500">This page is not available for this session.</p>
          <button
            type="button"
            onClick={() => window.location.assign("/dashboard")}
            className="mt-6 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white"
          >
            Return to workspace
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck size={17} /> One UCH Platform Operations
            </div>
            <div className="mt-1 text-xs text-slate-500">Internal access review</div>
          </div>
          <button
            type="button"
            onClick={() => window.location.assign("/dashboard")}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700"
          >
            Return to workspace
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Platform access</h1>
            <p className="mt-2 text-sm text-slate-500">
              Internal review of identity-verified registration requests.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50"
          >
            <RefreshCw size={16} /> Refresh
          </button>
        </div>

        {filter === "pending" && !approvalReady ? (
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Access granting is temporarily unavailable until production approval-email delivery is enabled. Rejection remains available and sends no email.
          </div>
        ) : null}

        {message ? (
          <div className="mt-6 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
            {message}
          </div>
        ) : null}

        <div className="mt-6 inline-flex rounded-xl border border-slate-200 bg-white p-1">
          {FILTERS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setFilter(value)}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                filter === value ? "bg-slate-950 text-white" : "text-slate-600"
              }`}
            >
              {value[0].toUpperCase() + value.slice(1)}
            </button>
          ))}
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          {loading ? (
            <div className="px-6 py-16 text-center text-sm text-slate-500">Loading access requests...</div>
          ) : items.length === 0 ? (
            <div className="px-6 py-16 text-center text-sm text-slate-500">No {filter} requests.</div>
          ) : (
            <div className="divide-y divide-slate-200">
              {items.map((registration) => {
                const user = registration.user || {};
                const name = `${user.first_name || ""} ${user.last_name || ""}`.trim() || "Applicant";
                const busy = busyId === registration.registration_id;

                return (
                  <div key={registration.registration_id} className="p-6">
                    <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="text-base font-semibold">{name}</div>
                        <div className="mt-1 text-sm text-slate-600">{user.email}</div>
                        <div className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
                          <div><span className="text-slate-400">Workspace:</span> {registration.organization_name}</div>
                          <div><span className="text-slate-400">Identity:</span> {registration.provider}</div>
                          <div><span className="text-slate-400">Status:</span> {registration.status}</div>
                        </div>
                        {registration.status === "rejected" && registration.review?.rejection_reason ? (
                          <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                            Internal reason: {registration.review.rejection_reason}
                          </div>
                        ) : null}
                      </div>

                      {registration.status === "pending" ? (
                        <div className="flex shrink-0 gap-2">
                          {approvalReady ? (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => void allowAccess(registration)}
                              className="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                            >
                              Allow access
                            </button>
                          ) : null}
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void rejectAccess(registration)}
                            className="inline-flex items-center gap-2 rounded-xl border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 disabled:opacity-50"
                          >
                            <XCircle size={16} /> Reject
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
