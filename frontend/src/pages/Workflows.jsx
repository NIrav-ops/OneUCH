import {useCallback,useEffect,useState,} from "react";
import { useNavigate } from "react-router-dom";
import {
  GitBranch,
  Play,
  ExternalLink,
  RefreshCw,
} from "lucide-react";

import {
  getWorkflowDefinitions,
} from "../services/workflow";


function normalizeWorkflowList(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  if (Array.isArray(data?.workflows)) {
    return data.workflows;
  }

  return [];
}


export default function Workflows() {
  const navigate = useNavigate();

  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");


  const loadWorkflows = useCallback(
    async () => {
    try {
      setError("");

      const data =
        await getWorkflowDefinitions();

      setWorkflows(
        normalizeWorkflowList(data)
      );
    } catch (err) {
      console.error(
        "Workflow loading failed:",
        err
      );

      setError(
        "Unable to load workflows."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);


  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);


  const handleRefresh = async () => {
    setRefreshing(true);
    await loadWorkflows();
  };


  return (
    <div className="p-6 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">

        <div>
          <div className="flex items-center gap-3">
            <GitBranch
              size={24}
              className="text-slate-700"
            />

            <h1 className="text-2xl font-semibold">
              Workflows
            </h1>
          </div>

          <p className="mt-1 text-sm text-slate-500">
            Manage business workflows,
            execution and operational automation.
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


      {/* Error */}
      {error && (
        <div
          className="
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
          {error}
        </div>
      )}


      {/* Loading */}
      {loading && (
        <div
          className="
            rounded-xl
            border
            border-slate-200
            bg-white
            p-8
            text-center
            text-sm
            text-slate-500
          "
        >
          Loading workflows...
        </div>
      )}


      {/* Empty */}
      {!loading &&
        !error &&
        workflows.length === 0 && (
          <div
            className="
              rounded-2xl
              border
              border-dashed
              border-slate-300
              bg-white
              p-12
              text-center
            "
          >
            <GitBranch
              size={32}
              className="
                mx-auto
                mb-3
                text-slate-400
              "
            />

            <h2 className="text-lg font-medium">
              No workflows found
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Workflow definitions will appear here
              when they are available.
            </p>
          </div>
        )}


      {/* Workflow list */}
      {!loading &&
        workflows.length > 0 && (
          <div className="grid gap-4">

            {workflows.map((workflow) => {

              const workflowId =
                workflow.id ||
                workflow.pk ||
                workflow.uuid;

              const workflowName =
                workflow.name ||
                workflow.title ||
                "Unnamed workflow";

              const workflowCode =
                workflow.code ||
                "—";

              const workflowVersion =
                workflow.version ??
                "—";

              const workflowStatus =
                workflow.status ||
                (
                  workflow.is_published
                    ? "Published"
                    : "Draft"
                );


              return (
                <div
                  key={workflowId}
                  className="
                    rounded-2xl
                    border
                    border-slate-200
                    bg-white
                    p-5
                    shadow-sm
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

                    <div className="min-w-0">

                      <div
                        className="
                          flex
                          items-center
                          gap-3
                        "
                      >
                        <div
                          className="
                            flex
                            h-10
                            w-10
                            shrink-0
                            items-center
                            justify-center
                            rounded-xl
                            bg-slate-100
                          "
                        >
                          <GitBranch
                            size={19}
                            className="text-slate-700"
                          />
                        </div>

                        <div className="min-w-0">

                          <h2
                            className="
                              truncate
                              text-base
                              font-semibold
                              text-slate-900
                            "
                          >
                            {workflowName}
                          </h2>

                          <p
                            className="
                              mt-0.5
                              text-xs
                              text-slate-500
                            "
                          >
                            Code: {workflowCode}
                          </p>

                        </div>
                      </div>

                    </div>


                    <span
                      className="
                        shrink-0
                        rounded-full
                        bg-slate-100
                        px-3
                        py-1
                        text-xs
                        font-medium
                        text-slate-700
                      "
                    >
                      {workflowStatus}
                    </span>

                  </div>


                  <div
                    className="
                      mt-5
                      flex
                      flex-wrap
                      items-center
                      gap-3
                      text-sm
                    "
                  >

                    <div
                      className="
                        rounded-lg
                        bg-slate-50
                        px-3
                        py-2
                        text-slate-600
                      "
                    >
                      Version:
                      <span className="ml-1 font-medium">
                        {workflowVersion}
                      </span>
                    </div>

                  </div>


                  <div
                    className="
                      mt-5
                      flex
                      flex-wrap
                      gap-2
                    "
                  >

                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/workflows/${workflowId}`
                        )
                      }
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
                      "
                    >
                      <ExternalLink
                        size={15}
                      />

                      Open
                    </button>


                    <button
                      type="button"
                      disabled
                      title="
                        Runtime execution will be
                        enabled from the execution
                        view.
                      "
                      className="
                        flex
                        cursor-not-allowed
                        items-center
                        gap-2
                        rounded-xl
                        border
                        border-slate-200
                        px-4
                        py-2
                        text-sm
                        font-medium
                        text-slate-400
                      "
                    >
                      <Play size={15} />

                      Run
                    </button>

                  </div>

                </div>
              );
            })}

          </div>
        )}

    </div>
  );
}