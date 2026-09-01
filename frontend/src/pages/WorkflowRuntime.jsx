import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleDashed,
  Clock3,
  Play,
  RefreshCw,
  Square,
  AlertCircle,
} from "lucide-react";
import {
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  getWorkflowRuntime,
  executeWorkflowRuntime,
  getWorkflowExecutionHistory,
} from "../services/workflow";


function formatStatus(status) {
  if (!status) {
    return "Unknown";
  }

  return String(status)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase()
    );
}


function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}


function formatDetails(details) {
  if (
    details === null ||
    details === undefined
  ) {
    return "—";
  }

  if (typeof details === "string") {
    return details;
  }

  try {
    return JSON.stringify(
      details,
      null,
      2
    );
  } catch {
    return String(details);
  }
}


function isTerminalStatus(status) {
  return [
    "completed",
    "failed",
    "cancelled",
  ].includes(
    String(status || "").toLowerCase()
  );
}


export default function WorkflowRuntime() {
  const navigate = useNavigate();
  const { instanceId } = useParams();

  const [runtime, setRuntime] = useState(null);
  const [history, setHistory] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [executing, setExecuting] = useState(false);

  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  const loadRuntime = useCallback(
    async () => {
      try {
        setError("");

        const [
          runtimeData,
          historyData,
        ] = await Promise.all([
          getWorkflowRuntime(instanceId),
          getWorkflowExecutionHistory(
            instanceId
          ),
        ]);

        setRuntime(runtimeData);

        setHistory(
          Array.isArray(
            historyData?.events
          )
            ? historyData.events
            : []
        );
      } catch (err) {
        console.error(
          "Workflow runtime loading failed:",
          err
        );

        setError(
          "Unable to load workflow runtime."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [instanceId]
  );


  useEffect(() => {
    loadRuntime();
  }, [loadRuntime]);


  const handleRefresh = async () => {
    setRefreshing(true);
    await loadRuntime();
  };


  const executeAction = async (
    action
  ) => {
    try {
      setActionError("");
      setExecuting(true);

      await executeWorkflowRuntime(
        instanceId,
        action
      );

      await loadRuntime();
    } catch (err) {
      console.error(
        `Workflow runtime ${action} failed:`,
        err
      );

      setActionError(
        err.response?.data?.detail ||
          `Unable to ${action} workflow.`
      );
    } finally {
      setExecuting(false);
    }
  };


  const status = String(
    runtime?.status || ""
  ).toLowerCase();


  const terminal = useMemo(
    () => isTerminalStatus(status),
    [status]
  );


  const canCancel =
    status === "running";


  if (loading) {
    return (
      <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
        <div
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-10
            text-center
            text-sm
            text-slate-500
          "
        >
          Loading workflow runtime...
        </div>
      </div>
    );
  }


  if (error) {
    return (
      <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7 space-y-4">

        <button
          type="button"
          onClick={() =>
            navigate("/workflows")
          }
          className="
            flex
            items-center
            gap-2
            text-sm
            text-slate-600
            hover:text-slate-900
          "
        >
          <ArrowLeft size={16} />
          Back to workflows
        </button>

        <div
          className="
            flex
            items-center
            gap-3
            rounded-xl
            border
            border-red-200
            bg-red-50
            px-4
            py-3
            text-sm
            text-red-700
          "
        >
          <AlertCircle size={18} />
          {error}
        </div>

      </div>
    );
  }


  return (
    <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

      <div className="mx-auto max-w-[1540px] space-y-5">


        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 text-white shadow-sm">

          <div className="absolute right-0 top-0 h-56 w-56 rounded-full bg-sky-500/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <button
              type="button"
              onClick={() =>
                navigate(
                  "/workflows"
                )
              }
              className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white"
            >

              <ArrowLeft
                size={14}
              />

              Back to workflows

            </button>


            <div className="mt-5 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">

              <div>

                <div className="inline-flex rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.17em] text-slate-300">
                  Governed runtime
                </div>

                <h1 className="mt-4 text-3xl font-semibold tracking-tight lg:text-4xl">
                  Workflow Runtime
                </h1>

                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                  Inspect authoritative runtime state and immutable workflow execution events.
                </p>

              </div>


              <div className="flex flex-wrap items-center gap-2">

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-200">
                  {formatStatus(
                    runtime?.status
                  )}
                </span>


                <button
                  type="button"
                  onClick={
                    handleRefresh
                  }
                  disabled={
                    refreshing
                  }
                  className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-xs font-semibold text-slate-950 hover:bg-slate-100 disabled:opacity-50"
                >

                  <RefreshCw
                    size={14}
                    className={
                      refreshing
                        ? "animate-spin"
                        : ""
                    }
                  />

                  Refresh

                </button>

              </div>

            </div>

          </div>

        </section>


        {actionError && (

          <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-700">

            <AlertCircle
              size={17}
              className="mt-0.5 shrink-0"
            />

            {actionError}

          </div>

        )}


        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Status
            </p>

            <div className="mt-3 flex items-center gap-2">

              {terminal ? (

                <CheckCircle2
                  size={17}
                  className="text-emerald-600"
                />

              ) : (

                <CircleDashed
                  size={17}
                  className="text-sky-600"
                />

              )}

              <span className="text-sm font-semibold text-slate-800">
                {formatStatus(
                  runtime?.status
                )}
              </span>

            </div>

          </div>


          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Workflow
            </p>

            <p className="mt-3 break-all text-sm font-semibold text-slate-800">
              {runtime?.workflow ||
                "?"}
            </p>

          </div>


          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Started
            </p>

            <div className="mt-3 flex items-start gap-2">

              <Clock3
                size={15}
                className="mt-0.5 text-slate-400"
              />

              <span className="text-xs font-semibold leading-5 text-slate-700">
                {formatDate(
                  runtime?.started_at
                )}
              </span>

            </div>

          </div>


          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Completed
            </p>

            <p className="mt-3 text-xs font-semibold leading-5 text-slate-700">
              {formatDate(
                runtime?.completed_at
              )}
            </p>

          </div>

        </section>


        {!terminal && (

          <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">

            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-500">
              Runtime control
            </p>

            <h2 className="mt-1 text-base font-semibold text-slate-950">
              Execution controls
            </h2>

            <p className="mt-2 text-xs leading-5 text-slate-500">
              Runtime actions change execution state without altering the published workflow definition.
            </p>


            <div className="mt-4 flex flex-wrap gap-2">

              {canCancel && (

                <button
                  type="button"
                  disabled={
                    executing
                  }
                  onClick={() =>
                    executeAction(
                      "cancel"
                    )
                  }
                  className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                >

                  <Square
                    size={14}
                  />

                  {executing
                    ? "Processing..."
                    : "Cancel runtime"}

                </button>

              )}

            </div>

          </section>

        )}


        <section
          id="history"
          className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm"
        >

          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">

            <div>

              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-sky-500">
                Immutable audit trail
              </p>

              <h2 className="mt-1 text-base font-semibold text-slate-950">
                Execution history
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Events recorded by the workflow execution layer.
              </p>

            </div>


            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
              {history.length} events
            </span>

          </div>


          {history.length ===
          0 ? (

            <div className="px-6 py-14 text-center">

              <p className="text-sm font-medium text-slate-600">
                No execution events recorded yet
              </p>

            </div>

          ) : (

            <div className="divide-y divide-slate-100">

              {history.map(
                (
                  event,
                  index
                ) => (

                  <article
                    key={
                      event.id ||
                      `${event.event}-${index}`
                    }
                    className="px-5 py-4 sm:px-6"
                  >

                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">

                      <div>

                        <p className="text-sm font-semibold text-slate-900">
                          {formatStatus(
                            event.event
                          )}
                        </p>


                        {event.node && (

                          <p className="mt-1 text-xs text-slate-500">
                            Node: {event.node}
                          </p>

                        )}

                      </div>


                      <span className="text-xs text-slate-400">
                        {formatDate(
                          event.created_at ||
                          event.timestamp
                        )}
                      </span>

                    </div>


                    {event.details && (

                      <pre className="mt-3 overflow-x-auto rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                        {formatDetails(
                          event.details
                        )}
                      </pre>

                    )}

                  </article>

                )
              )}

            </div>

          )}

        </section>

      </div>

    </div>
  );

}
