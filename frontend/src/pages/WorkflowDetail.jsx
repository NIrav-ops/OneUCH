import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useNavigate, useParams } from "react-router-dom";

import {
  ArrowLeft,
  GitBranch,
  RefreshCw,
  Upload,
  CheckCircle2,
  CircleDashed,
  AlertCircle,
  Play,
  History,
  LoaderCircle,
} from "lucide-react";

import {
  getWorkflowDefinition,
  getWorkflowGraph,
  publishWorkflow,
  createWorkflowRuntime,
  executeWorkflowRuntime,
  getWorkflowRuntime,
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


function getNodeLabel(node) {
  return (
    node.name ||
    node.node_type ||
    "Unnamed node"
  );
}


function getRuntimeStatusClass(status) {
  switch (status) {
    case "running":
      return "bg-blue-50 text-blue-700 border-blue-200";

    case "completed":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";

    case "failed":
      return "bg-red-50 text-red-700 border-red-200";

    case "cancelled":
      return "bg-slate-100 text-slate-700 border-slate-200";

    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
}


export default function WorkflowDetail() {
  const navigate = useNavigate();

  const { workflowId } = useParams();

  const [workflow, setWorkflow] = useState(null);

  const [graph, setGraph] = useState(null);

  const [runtime, setRuntime] = useState(null);

  const [executionHistory, setExecutionHistory] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [publishing, setPublishing] =
    useState(false);

  const [starting, setStarting] =
    useState(false);

  const [loadingRuntime, setLoadingRuntime] =
    useState(false);

  const [error, setError] =
    useState("");

  const [publishError, setPublishError] =
    useState("");

  const [runtimeError, setRuntimeError] =
    useState("");

  const loadWorkflow = useCallback(
    async () => {
      try {
        setError("");

        const [
          workflowData,
          graphData,
        ] = await Promise.all([
          getWorkflowDefinition(workflowId),
          getWorkflowGraph(workflowId),
        ]);

        setWorkflow(workflowData);
        setGraph(graphData);
      } catch (err) {
        console.error(
          "Workflow detail loading failed:",
          err
        );

        setError(
          "Unable to load workflow details."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [workflowId]
  );


  useEffect(() => {
    loadWorkflow();
  }, [loadWorkflow]);


  const handleRefresh = async () => {
    setRefreshing(true);

    await loadWorkflow();

    if (runtime?.id) {
      await loadRuntime(runtime.id);
    }
  };


  const handlePublish = async () => {
    if (!workflowId) {
      return;
    }

    try {
      setPublishError("");

      setPublishing(true);

      const response =
        await publishWorkflow(
          workflowId
        );

      const publishedWorkflow =
        response?.workflow;

      if (publishedWorkflow) {
        setWorkflow((current) => ({
          ...current,
          ...publishedWorkflow,
        }));
      } else {
        const refreshed =
          await getWorkflowDefinition(
            workflowId
          );

        setWorkflow(refreshed);
      }

      const refreshedGraph =
        await getWorkflowGraph(
          workflowId
        );

      setGraph(refreshedGraph);
    } catch (err) {
      console.error(
        "Workflow publish failed:",
        err
      );

      setPublishError(
        err.response?.data?.detail ||
          "Unable to publish workflow."
      );
    } finally {
      setPublishing(false);
    }
  };


  const loadRuntime = useCallback(
    async (instanceId) => {
      if (!instanceId) {
        return;
      }

      try {
        setLoadingRuntime(true);
        setRuntimeError("");

        const [
          runtimeData,
          historyData,
        ] = await Promise.all([
          getWorkflowRuntime(
            instanceId
          ),
          getWorkflowExecutionHistory(
            instanceId
          ),
        ]);

        setRuntime(runtimeData);

        setExecutionHistory(
          Array.isArray(historyData?.events)
            ? historyData.events
            : []
        );
      } catch (err) {
        console.error(
          "Workflow runtime loading failed:",
          err
        );

        setRuntimeError(
          err.response?.data?.detail ||
            "Unable to load workflow runtime."
        );
      } finally {
        setLoadingRuntime(false);
      }
    },
    []
  );

  const isActive =
    workflow?.status === "active";


  const handleStartWorkflow = async () => {
  if (!workflowId || !isActive) {
    return;
  }

  try {
    setStarting(true);
    setRuntimeError("");

    // Step 1: Create the runtime instance.
    const runtimeData = await createWorkflowRuntime(
      workflowId,
      {}
    );

    const instanceId =
      runtimeData?.id ||
      runtimeData?.instance_id;

    if (!instanceId) {
      throw new Error(
        "Workflow runtime instance was created without an instance ID."
      );
    }

    // Step 2: Execute the newly-created runtime instance.
    await executeWorkflowRuntime(
      instanceId,
      "run"
    );

    // Step 3: Load authoritative runtime state/history.
    await loadRuntime(instanceId);

  } catch (err) {
    console.error(
      "Workflow runtime execution failed:",
      err
    );

    setRuntimeError(
      err.response?.data?.detail ||
        err.message ||
        "Unable to start workflow."
    );
  } finally {
    setStarting(false);
  }
};


  const nodes = useMemo(
    () =>
      Array.isArray(graph?.nodes)
        ? graph.nodes
        : [],
    [graph]
  );


  const transitions = useMemo(
    () =>
      Array.isArray(graph?.transitions)
        ? graph.transitions
        : [],
    [graph]
  );

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
          Loading workflow...
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

          <div className="flex items-center gap-3">

            <div
              className="
                flex
                h-11
                w-11
                items-center
                justify-center
                rounded-xl
                bg-slate-100
              "
            >
              <GitBranch
                size={21}
                className="text-slate-700"
              />
            </div>

            <div>

              <h1
                className="
                  text-2xl
                  font-semibold
                  text-slate-900
                "
              >
                {workflow?.name ||
                  "Unnamed workflow"}
              </h1>

              <p
                className="
                  mt-1
                  text-sm
                  text-slate-500
                "
              >
                {workflow?.code ||
                  "No workflow code"}
              </p>

            </div>

          </div>

        </div>


        <div
          className="
            flex
            flex-wrap
            items-center
            gap-2
          "
        >

          <button
            type="button"
            onClick={handleRefresh}
            disabled={
              refreshing ||
              loadingRuntime
            }
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


          {!isActive && (
            <button
              type="button"
              onClick={handlePublish}
              disabled={publishing}
              className="
                flex
                items-center
                gap-2
                rounded-xl
                bg-slate-900
                px-4
                py-2
                text-sm
                font-medium
                text-white
                hover:bg-slate-800
                disabled:opacity-50
              "
            >
              <Upload size={16} />

              {publishing
                ? "Publishing..."
                : "Publish"}
            </button>
          )}


          {isActive && !runtime && (
            <button
              type="button"
              onClick={
                handleStartWorkflow
              }
              disabled={starting}
              className="
                flex
                items-center
                gap-2
                rounded-xl
                bg-emerald-600
                px-4
                py-2
                text-sm
                font-medium
                text-white
                hover:bg-emerald-700
                disabled:opacity-50
              "
            >
              {starting ? (
                <LoaderCircle
                  size={16}
                  className="animate-spin"
                />
              ) : (
                <Play size={16} />
              )}

              {starting
                ? "Starting..."
                : "Start Workflow"}
            </button>
          )}

        </div>

      </div>


      {/* Publish error */}

      {publishError && (
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
          {publishError}
        </div>
      )}


      {/* Runtime error */}

      {runtimeError && (
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
          {runtimeError}
        </div>
      )}


      {/* Runtime */}

      {runtime && (
        <section
          className="
            rounded-2xl
            border
            border-blue-200
            bg-white
            p-6
          "
        >

          <div
            className="
              flex
              flex-col
              gap-4
              md:flex-row
              md:items-start
              md:justify-between
            "
          >

            <div>

              <div
                className="
                  flex
                  items-center
                  gap-2
                "
              >
                <Play
                  size={18}
                  className="text-blue-600"
                />

                <h2
                  className="
                    text-base
                    font-semibold
                    text-slate-900
                  "
                >
                  Current execution
                </h2>
              </div>

              <p
                className="
                  mt-1
                  text-sm
                  text-slate-500
                "
              >
                Runtime instance created from
                this workflow definition.
              </p>

            </div>


            <span
              className={`
                rounded-full
                border
                px-3
                py-1
                text-xs
                font-medium
                ${getRuntimeStatusClass(
                  runtime.status
                )}
              `}
            >
              {formatStatus(
                runtime.status
              )}
            </span>

          </div>


          <div
            className="
              mt-5
              grid
              gap-4
              md:grid-cols-3
            "
          >

            <div>
              <p className="text-xs text-slate-500">
                Instance ID
              </p>

              <p
                className="
                  mt-1
                  break-all
                  text-sm
                  font-medium
                  text-slate-900
                "
              >
                {runtime.id ||
                  runtime.instance_id ||
                  "—"}
              </p>
            </div>


            <div>
              <p className="text-xs text-slate-500">
                Workflow
              </p>

              <p className="mt-1 text-sm font-medium">
                {runtime.workflow ||
                  workflow?.id ||
                  "—"}
              </p>
            </div>


            <div>
              <p className="text-xs text-slate-500">
                Started
              </p>

              <p className="mt-1 text-sm font-medium">
                {runtime.started_at
                  ? new Date(
                      runtime.started_at
                    ).toLocaleString()
                  : "—"}
              </p>
            </div>

          </div>


          <div className="mt-5 flex flex-wrap gap-2">

            <button
              type="button"
              onClick={() => {
                const instanceId =
                  runtime.id ||
                  runtime.instance_id;

                if (instanceId) {
                  loadRuntime(
                    instanceId
                  );
                }
              }}
              disabled={loadingRuntime}
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
                size={15}
                className={
                  loadingRuntime
                    ? "animate-spin"
                    : ""
                }
              />

              Refresh execution
            </button>


            <button
              type="button"
              onClick={() => {
                const instanceId =
                  runtime.id ||
                  runtime.instance_id;

                if (instanceId) {
                  navigate(
                    `/workflows/runtime/${instanceId}`
                  );
                }
              }}
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
              "
            >
              <Play size={15} />
              Open Runtime
            </button>


            <button
              type="button"
              onClick={() => {
                const instanceId =
                  runtime.id ||
                  runtime.instance_id;

                if (instanceId) {
                  navigate(
                    `/workflows/runtime/${instanceId}/history`
                  );
                }
              }}
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
              "
            >
              <History size={15} />
              Execution History
            </button>

          </div>

        </section>
      )}


      {/* Overview */}

      <div
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

            {isActive ? (
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
                workflow?.status
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
            Version
          </p>

          <p className="mt-2 text-lg font-semibold">
            {workflow?.version ?? "—"}
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
            Nodes
          </p>

          <p className="mt-2 text-lg font-semibold">
            {nodes.length}
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
            Transitions
          </p>

          <p className="mt-2 text-lg font-semibold">
            {transitions.length}
          </p>
        </div>

      </div>


      {/* Description */}

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
          Workflow definition
        </h2>

        <p
          className="
            mt-3
            whitespace-pre-wrap
            text-sm
            leading-6
            text-slate-600
          "
        >
          {workflow?.description ||
            "No description provided."}
        </p>

      </section>


      {/* Graph */}

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
              Workflow graph
            </h2>

            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              Current workflow structure returned
              by the workflow engine.
            </p>

          </div>

          {graph?.editable !== undefined && (
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
              {graph.editable
                ? "Editable"
                : "Read only"}
            </span>
          )}

        </div>


        {nodes.length === 0 ? (
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
            No workflow nodes defined.
          </div>
        ) : (
          <div className="mt-6 space-y-3">

            {nodes.map((node, index) => (
              <div
                key={
                  node.id ||
                  node.client_id ||
                  `node-${index}`
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
                    items-start
                    justify-between
                    gap-4
                  "
                >

                  <div>

                    <p
                      className="
                        font-medium
                        text-slate-900
                      "
                    >
                      {getNodeLabel(node)}
                    </p>

                    <p
                      className="
                        mt-1
                        text-xs
                        uppercase
                        tracking-wide
                        text-slate-500
                      "
                    >
                      {node.node_type}
                    </p>

                  </div>

                  <span
                    className="
                      rounded-lg
                      bg-white
                      px-2
                      py-1
                      text-xs
                      text-slate-500
                    "
                  >
                    #{index + 1}
                  </span>

                </div>

              </div>
            ))}

          </div>
        )}

      </section>


      {/* Transitions */}

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
          Transitions
        </h2>

        {transitions.length === 0 ? (
          <p
            className="
              mt-4
              text-sm
              text-slate-500
            "
          >
            No transitions defined.
          </p>
        ) : (
          <div className="mt-4 space-y-3">

            {transitions.map(
              (transition, index) => (
                <div
                  key={
                    transition.id ||
                    `transition-${index}`
                  }
                  className="
                    rounded-xl
                    border
                    border-slate-200
                    p-4
                  "
                >

                  <div
                    className="
                      grid
                      gap-3
                      md:grid-cols-4
                    "
                  >

                    <div>
                      <p className="text-xs text-slate-500">
                        Source
                      </p>

                      <p className="mt-1 text-sm font-medium break-all">
                        {transition.source}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs text-slate-500">
                        Target
                      </p>

                      <p className="mt-1 text-sm font-medium break-all">
                        {transition.target}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs text-slate-500">
                        Priority
                      </p>

                      <p className="mt-1 text-sm font-medium">
                        {transition.priority ?? 100}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs text-slate-500">
                        Condition
                      </p>

                      <p className="mt-1 text-sm font-medium break-words">
                        {transition.condition ||
                          "Always"}
                      </p>
                    </div>

                  </div>

                </div>
              )
            )}

          </div>
        )}

      </section>


      {/* Execution history preview */}

      {runtime && (
        <section
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-6
          "
        >

          <div className="flex items-center gap-2">

            <History
              size={18}
              className="text-slate-700"
            />

            <h2
              className="
                text-base
                font-semibold
                text-slate-900
              "
            >
              Execution history
            </h2>

          </div>


          {executionHistory.length === 0 ? (
            <p
              className="
                mt-4
                text-sm
                text-slate-500
              "
            >
              No execution events recorded yet.
            </p>
          ) : (
            <div className="mt-4 space-y-2">

              {executionHistory
                .slice(0, 10)
                .map((event, index) => (
                  <div
                    key={
                      event.id ||
                      `event-${index}`
                    }
                    className="
                      rounded-xl
                      border
                      border-slate-200
                      bg-slate-50
                      px-4
                      py-3
                    "
                  >

                    <div
                      className="
                        flex
                        flex-col
                        gap-1
                        md:flex-row
                        md:items-center
                        md:justify-between
                      "
                    >

                      <span
                        className="
                          text-sm
                          font-medium
                          text-slate-900
                        "
                      >
                        {formatStatus(
                          event.event
                        )}
                      </span>

                      {event.created_at && (
                        <span
                          className="
                            text-xs
                            text-slate-500
                          "
                        >
                          {new Date(
                            event.created_at
                          ).toLocaleString()}
                        </span>
                      )}

                    </div>

                  </div>
                ))}

            </div>
          )}

        </section>
      )}

    </div>
  );
}