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
      <div className="p-6">
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
      <div className="p-6 space-y-4">

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
    <div className="p-6 space-y-6">

      {/* Header */}

      <div
        className="
          flex
          flex-col
          gap-4
          lg:flex-row
          lg:items-start
          lg:justify-between
        "
      >

        <div>

          <button
            type="button"
            onClick={() =>
              navigate("/workflows")
            }
            className="
              mb-4
              flex
              items-center
              gap-2
              text-sm
              text-slate-500
              hover:text-slate-900
            "
          >
            <ArrowLeft size={16} />
            Back to workflows
          </button>

          <h1
            className="
              text-2xl
              font-semibold
              text-slate-900
            "
          >
            Workflow Runtime
          </h1>

          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Operational execution and
            accountability for this workflow.
          </p>

        </div>


        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          className="
            flex
            items-center
            gap-2
            rounded-xl
            border
            border-slate-300
            bg-white
            px-4
            py-2
            text-sm
            font-medium
            text-slate-700
            hover:bg-slate-50
            disabled:opacity-50
          "
        >
          <RefreshCw
            size={16}
            className={
              refreshing
                ? "animate-spin"
                : ""
            }
          />

          Refresh
        </button>

      </div>


      {actionError && (
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
          {actionError}
        </div>
      )}


      {/* Runtime overview */}

      <section
        className="
          grid
          gap-4
          md:grid-cols-4
        "
      >

        <div
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-5
          "
        >
          <p className="text-xs text-slate-500">
            Status
          </p>

          <div className="mt-2 flex items-center gap-2">

            {terminal ? (
              <CheckCircle2
                size={17}
                className="text-emerald-600"
              />
            ) : (
              <CircleDashed
                size={17}
                className="text-slate-500"
              />
            )}

            <span className="font-medium">
              {formatStatus(
                runtime?.status
              )}
            </span>

          </div>
        </div>


        <div
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-5
          "
        >
          <p className="text-xs text-slate-500">
            Workflow
          </p>

          <p className="mt-2 font-medium break-all">
            {runtime?.workflow || "—"}
          </p>
        </div>


        <div
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-5
          "
        >
          <p className="text-xs text-slate-500">
            Started
          </p>

          <div className="mt-2 flex gap-2">

            <Clock3
              size={16}
              className="text-slate-400"
            />

            <span className="text-sm">
              {formatDate(
                runtime?.started_at
              )}
            </span>

          </div>
        </div>


        <div
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-5
          "
        >
          <p className="text-xs text-slate-500">
            Completed
          </p>

          <p className="mt-2 text-sm">
            {formatDate(
              runtime?.completed_at
            )}
          </p>
        </div>

      </section>


      {/* Runtime controls */}

      {!terminal && (
        <section
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-6
          "
        >

          <h2
            className="
              text-base
              font-semibold
              text-slate-900
            "
          >
            Execution controls
          </h2>

          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Control the workflow runtime without
            changing its published definition.
          </p>

          <div
            className="
              mt-5
              flex
              flex-wrap
              gap-3
            "
          >


            {canCancel && (
              <button
                type="button"
                disabled={executing}
                onClick={() =>
                  executeAction("cancel")
                }
                className="
                  flex
                  items-center
                  gap-2
                  rounded-xl
                  border
                  border-red-300
                  bg-white
                  px-4
                  py-2
                  text-sm
                  font-medium
                  text-red-700
                  hover:bg-red-50
                  disabled:opacity-50
                "
              >
                <Square size={15} />
                Cancel
              </button>
            )}

          </div>

        </section>
      )}


      {/* Execution history */}

      <section
        className="
          rounded-2xl
          border
          border-slate-200
          bg-white
          p-6
        "
      >

        <div
          className="
            flex
            items-center
            justify-between
            gap-4
          "
        >

          <div>

            <h2
              className="
                text-base
                font-semibold
                text-slate-900
              "
            >
              Execution history
            </h2>

            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              Immutable runtime events recorded
              by the workflow execution layer.
            </p>

          </div>

          <span
            className="
              rounded-full
              bg-slate-100
              px-3
              py-1
              text-xs
              font-medium
              text-slate-600
            "
          >
            {history.length} events
          </span>

        </div>


        {history.length === 0 ? (
          <div
            className="
              mt-6
              rounded-xl
              border
              border-dashed
              border-slate-300
              p-8
              text-center
              text-sm
              text-slate-500
            "
          >
            No execution events recorded yet.
          </div>
        ) : (
          <div className="mt-6 space-y-3">

            {history.map(
              (event, index) => (
                <div
                  key={
                    event.id ||
                    `${event.event}-${index}`
                  }
                  className="
                    rounded-xl
                    border
                    border-slate-200
                    bg-slate-50
                    p-4
                  "
                >

                  <div
                    className="
                      flex
                      flex-col
                      gap-3
                      md:flex-row
                      md:items-start
                      md:justify-between
                    "
                  >

                    <div>

                      <p
                        className="
                          font-medium
                          text-slate-900
                        "
                      >
                        {formatStatus(
                          event.event
                        )}
                      </p>

                      {event.node && (
                        <p
                          className="
                            mt-1
                            text-xs
                            text-slate-500
                          "
                        >
                          Node: {event.node}
                        </p>
                      )}

                    </div>

                    <span
                      className="
                        text-xs
                        text-slate-500
                      "
                    >
                      {formatDate(
                        event.created_at ||
                          event.timestamp
                      )}
                    </span>

                  </div>


                  {event.details && (
                    <pre
                      className="
                        mt-3
                        overflow-x-auto
                        rounded-lg
                        bg-white
                        p-3
                        text-xs
                        text-slate-600
                      "
                    >
                      {formatDetails(
                        event.details
                      )}
                    </pre>
                  )}

                </div>
              )
            )}

          </div>
        )}

      </section>

    </div>
  );
}