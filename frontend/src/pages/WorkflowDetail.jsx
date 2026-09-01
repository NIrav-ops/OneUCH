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
    <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

      <div className="mx-auto max-w-[1540px] space-y-5">


        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 text-white shadow-sm">

          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-violet-500/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <button
              type="button"
              onClick={() =>
                navigate(
                  "/workflows"
                )
              }
              className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 transition hover:text-white"
            >

              <ArrowLeft
                size={14}
              />

              Back to workflows

            </button>


            <div className="mt-5 flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">

              <div className="max-w-3xl">

                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.17em] text-slate-300">

                  <GitBranch
                    size={14}
                  />

                  Workflow definition

                </div>


                <h1 className="mt-4 text-3xl font-semibold tracking-tight lg:text-4xl">
                  {workflow?.name ||
                    "Unnamed workflow"}
                </h1>


                <p className="mt-2 text-sm text-slate-300">
                  {workflow?.code ||
                    "No workflow code"}
                </p>


                <div className="mt-5 flex flex-wrap gap-2">

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                    {formatStatus(
                      workflow?.status
                    )}
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                    Version {workflow?.version ?? "?"}
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                    {nodes.length} nodes
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                    {transitions.length} transitions
                  </span>

                </div>

              </div>


              <div className="flex flex-wrap gap-2">

                <button
                  type="button"
                  onClick={
                    handleRefresh
                  }
                  disabled={
                    refreshing ||
                    loadingRuntime
                  }
                  className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-xs font-semibold text-white hover:bg-white/10 disabled:opacity-50"
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


                {!isActive && (

                  <button
                    type="button"
                    onClick={
                      handlePublish
                    }
                    disabled={
                      publishing
                    }
                    className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-xs font-semibold text-slate-950 hover:bg-slate-100 disabled:opacity-50"
                  >

                    <Upload
                      size={14}
                    />

                    {publishing
                      ? "Publishing..."
                      : "Publish"}

                  </button>

                )}


                {isActive &&
                  !runtime && (

                  <button
                    type="button"
                    onClick={
                      handleStartWorkflow
                    }
                    disabled={
                      starting
                    }
                    className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-semibold text-white hover:bg-emerald-600 disabled:opacity-50"
                  >

                    {starting ? (

                      <LoaderCircle
                        size={14}
                        className="animate-spin"
                      />

                    ) : (

                      <Play
                        size={14}
                      />

                    )}

                    {starting
                      ? "Starting..."
                      : "Start workflow"}

                  </button>

                )}

              </div>

            </div>

          </div>

        </section>


        {publishError && (

          <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-700">

            <AlertCircle
              size={17}
              className="mt-0.5 shrink-0"
            />

            {publishError}

          </div>

        )}


        {runtimeError && (

          <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-700">

            <AlertCircle
              size={17}
              className="mt-0.5 shrink-0"
            />

            {runtimeError}

          </div>

        )}


        {runtime && (

          <section className="rounded-[26px] border border-sky-200 bg-white p-5 shadow-sm sm:p-6">

            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">

              <div>

                <div className="flex items-center gap-2">

                  <Play
                    size={17}
                    className="text-sky-600"
                  />

                  <h2 className="text-base font-semibold text-slate-950">
                    Current execution
                  </h2>

                </div>


                <p className="mt-2 text-xs text-slate-500">
                  Runtime instance created from this published workflow definition.
                </p>

              </div>


              <span
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${getRuntimeStatusClass(
                  runtime.status
                )}`}
              >
                {formatStatus(
                  runtime.status
                )}
              </span>

            </div>


            <div className="mt-5 grid gap-3 sm:grid-cols-3">

              <div className="rounded-xl bg-slate-50 p-3">

                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  Instance
                </p>

                <p className="mt-1 break-all text-xs font-semibold text-slate-700">
                  {runtime.id ||
                    runtime.instance_id ||
                    "?"}
                </p>

              </div>


              <div className="rounded-xl bg-slate-50 p-3">

                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  Workflow
                </p>

                <p className="mt-1 break-all text-xs font-semibold text-slate-700">
                  {runtime.workflow ||
                    workflow?.id ||
                    "?"}
                </p>

              </div>


              <div className="rounded-xl bg-slate-50 p-3">

                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  Events
                </p>

                <p className="mt-1 text-xs font-semibold text-slate-700">
                  {executionHistory.length}
                </p>

              </div>

            </div>


            <div className="mt-4 flex flex-wrap gap-2">

              <button
                type="button"
                onClick={() => {

                  const instanceId =
                    runtime.id ||
                    runtime.instance_id;


                  if (instanceId) {

                    navigate(
                      `/workflows/${workflowId}/runtime/${instanceId}`
                    );

                  }

                }}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white hover:bg-slate-800"
              >

                <Play
                  size={14}
                />

                Open runtime

              </button>


              <button
                type="button"
                onClick={() => {

                  const instanceId =
                    runtime.id ||
                    runtime.instance_id;


                  if (instanceId) {

                    navigate(
                      `/workflows/${workflowId}/runtime/${instanceId}#history`
                    );

                  }

                }}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >

                <History
                  size={14}
                />

                Execution history

              </button>

            </div>

          </section>

        )}


        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Status
            </p>

            <div className="mt-3 flex items-center gap-2">

              {isActive ? (

                <CheckCircle2
                  size={17}
                  className="text-emerald-600"
                />

              ) : (

                <CircleDashed
                  size={17}
                  className="text-slate-400"
                />

              )}

              <span className="text-sm font-semibold text-slate-800">
                {formatStatus(
                  workflow?.status
                )}
              </span>

            </div>

          </div>


          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Version
            </p>

            <p className="mt-3 text-xl font-semibold text-slate-950">
              {workflow?.version ?? "?"}
            </p>

          </div>


          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Nodes
            </p>

            <p className="mt-3 text-xl font-semibold text-slate-950">
              {nodes.length}
            </p>

          </div>


          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Transitions
            </p>

            <p className="mt-3 text-xl font-semibold text-slate-950">
              {transitions.length}
            </p>

          </div>

        </section>


        <div className="grid gap-5 xl:grid-cols-2">

          <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

            <div className="border-b border-slate-100 px-5 py-4">

              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-indigo-500">
                Workflow graph
              </p>

              <h2 className="mt-1 text-base font-semibold text-slate-950">
                Nodes
              </h2>

            </div>


            {nodes.length ===
            0 ? (

              <div className="px-5 py-10 text-center text-xs text-slate-400">
                No nodes defined.
              </div>

            ) : (

              <div className="divide-y divide-slate-100">

                {nodes.map(
                  (
                    node,
                    index
                  ) => (

                    <div
                      key={
                        node.id ||
                        node.pk ||
                        `node-${index}`
                      }
                      className="px-5 py-4"
                    >

                      <p className="text-sm font-semibold text-slate-900">
                        {getNodeLabel(
                          node
                        )}
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        {formatStatus(
                          node.node_type ||
                          "node"
                        )}
                      </p>

                    </div>

                  )
                )}

              </div>

            )}

          </section>


          <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

            <div className="border-b border-slate-100 px-5 py-4">

              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-500">
                Execution path
              </p>

              <h2 className="mt-1 text-base font-semibold text-slate-950">
                Transitions
              </h2>

            </div>


            {transitions.length ===
            0 ? (

              <div className="px-5 py-10 text-center text-xs text-slate-400">
                No transitions defined.
              </div>

            ) : (

              <div className="divide-y divide-slate-100">

                {transitions.map(
                  (
                    transition,
                    index
                  ) => (

                    <div
                      key={
                        transition.id ||
                        `transition-${index}`
                      }
                      className="px-5 py-4"
                    >

                      <div className="grid gap-3 sm:grid-cols-3">

                        <div>

                          <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                            From
                          </p>

                          <p className="mt-1 break-words text-xs font-semibold text-slate-700">
                            {transition.source_node ||
                              transition.from_node ||
                              transition.source ||
                              "?"}
                          </p>

                        </div>


                        <div>

                          <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                            To
                          </p>

                          <p className="mt-1 break-words text-xs font-semibold text-slate-700">
                            {transition.target_node ||
                              transition.to_node ||
                              transition.target ||
                              "?"}
                          </p>

                        </div>


                        <div>

                          <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                            Priority
                          </p>

                          <p className="mt-1 text-xs font-semibold text-slate-700">
                            {transition.priority ?? 100}
                          </p>

                        </div>

                      </div>


                      <div className="mt-3 rounded-xl bg-slate-50 px-3 py-2">

                        <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                          Condition
                        </p>

                        <p className="mt-1 break-words text-xs text-slate-600">
                          {transition.condition ||
                            "Always"}
                        </p>

                      </div>

                    </div>

                  )
                )}

              </div>

            )}

          </section>

        </div>


        {runtime && (

          <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">

              <div>

                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-sky-500">
                  Runtime audit
                </p>

                <h2 className="mt-1 text-base font-semibold text-slate-950">
                  Execution history
                </h2>

              </div>


              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
                {executionHistory.length}
              </span>

            </div>


            {executionHistory.length ===
            0 ? (

              <div className="px-5 py-10 text-center text-xs text-slate-400">
                No execution events recorded yet.
              </div>

            ) : (

              <div className="divide-y divide-slate-100">

                {executionHistory
                  .slice(
                    0,
                    10
                  )
                  .map(
                    (
                      event,
                      index
                    ) => (

                      <div
                        key={
                          event.id ||
                          `event-${index}`
                        }
                        className="flex flex-col gap-2 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
                      >

                        <span className="text-sm font-semibold text-slate-800">
                          {formatStatus(
                            event.event
                          )}
                        </span>


                        {event.created_at && (

                          <span className="text-xs text-slate-400">
                            {new Date(
                              event.created_at
                            ).toLocaleString()}
                          </span>

                        )}

                      </div>

                    )
                  )}

              </div>

            )}

          </section>

        )}

      </div>

    </div>
  );

}
