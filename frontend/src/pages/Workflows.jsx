import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  ExternalLink,
  GitBranch,
  Play,
  RefreshCw,
} from "lucide-react";

import {
  getWorkflowDefinitions,
} from "../services/workflow";


function normalizeWorkflowList(
  data
) {

  if (Array.isArray(data)) {
    return data;
  }


  if (
    Array.isArray(
      data?.results
    )
  ) {
    return data.results;
  }


  if (
    Array.isArray(
      data?.workflows
    )
  ) {
    return data.workflows;
  }


  return [];

}


export default function Workflows() {

  const navigate =
    useNavigate();


  const [
    workflows,
    setWorkflows,
  ] = useState([]);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    refreshing,
    setRefreshing,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  const loadWorkflows =
    useCallback(
      async () => {

        try {

          setError(
            ""
          );


          const data =
            await getWorkflowDefinitions();


          setWorkflows(
            normalizeWorkflowList(
              data
            )
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

          setLoading(
            false
          );

          setRefreshing(
            false
          );

        }

      },
      []
    );


  useEffect(
    () => {

      loadWorkflows();

    },
    [
      loadWorkflows,
    ]
  );


  const handleRefresh =
    async () => {

      setRefreshing(
        true
      );

      await loadWorkflows();

    };


  const publishedCount =
    workflows.filter(
      (workflow) =>
        workflow.status ===
          "active"
        ||
        workflow.status ===
          "published"
        ||
        workflow.is_published
    ).length;


  const draftCount =
    Math.max(
      0,
      workflows.length -
      publishedCount
    );


  return (
    <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

      <div className="mx-auto max-w-[1540px]">


        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 text-white shadow-sm">

          <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-violet-500/10 blur-3xl" />

          <div className="relative flex flex-col gap-6 px-6 py-7 lg:flex-row lg:items-end lg:justify-between lg:px-8 lg:py-8">

            <div className="max-w-3xl">

              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.17em] text-slate-300">

                <GitBranch
                  size={14}
                />

                Governed automation

              </div>


              <h1 className="mt-5 text-3xl font-semibold tracking-tight text-white lg:text-4xl">
                Workflows
              </h1>


              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                Govern repeatable execution without disconnecting automation from communication, ownership and accountability.
              </p>


              <div className="mt-5 flex flex-wrap gap-2">

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Version controlled
                </span>

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Published explicitly
                </span>

                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium text-slate-300">
                  Runtime accountable
                </span>

              </div>

            </div>


            <button
              type="button"
              onClick={
                handleRefresh
              }
              disabled={
                refreshing
              }
              className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >

              <RefreshCw
                size={16}
                className={
                  refreshing
                    ? "animate-spin"
                    : ""
                }
              />

              {refreshing
                ? "Refreshing..."
                : "Refresh workflows"}

            </button>

          </div>

        </section>


        {error && (

          <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-700">
            {error}
          </div>

        )}


        <section className="mt-5 grid gap-3 sm:grid-cols-3">

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
              Definitions
            </p>

            <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              {workflows.length}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              Workflow definitions available to this workspace.
            </p>

          </div>


          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Published
            </p>

            <p className="mt-3 text-3xl font-semibold tracking-tight text-emerald-800">
              {publishedCount}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              Definitions currently available for governed execution.
            </p>

          </div>


          <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Draft
            </p>

            <p className="mt-3 text-3xl font-semibold tracking-tight text-amber-800">
              {draftCount}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              Definitions not yet published into active execution.
            </p>

          </div>

        </section>


        {loading ? (

          <section className="mt-5 rounded-[26px] border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">

            <div className="mx-auto h-8 w-8 animate-pulse rounded-full bg-slate-200" />

            <p className="mt-4 text-sm font-medium text-slate-500">
              Loading workflow definitions...
            </p>

          </section>

        ) : workflows.length ===
          0 ? (

          <section className="mt-5 rounded-[26px] border border-dashed border-slate-300 bg-white px-6 py-16 text-center shadow-sm">

            <GitBranch
              size={32}
              className="mx-auto text-slate-300"
            />

            <h2 className="mt-4 text-lg font-semibold text-slate-800">
              No workflows found
            </h2>

            <p className="mt-2 text-sm text-slate-500">
              Workflow definitions will appear here when they are available.
            </p>

          </section>

        ) : (

          <section className="mt-5 overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

            <div className="border-b border-slate-100 px-5 py-4 sm:px-6">

              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-500">
                Automation library
              </p>

              <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                Workflow definitions
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Open a workflow to inspect its graph, publish it and manage runtime execution.
              </p>

            </div>


            <div className="grid gap-0 divide-y divide-slate-100">

              {workflows.map(
                (workflow) => {

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
                    "?";


                  const workflowVersion =
                    workflow.version ??
                    "?";


                  const workflowStatus =
                    workflow.status ||
                    (
                      workflow.is_published
                        ? "Published"
                        : "Draft"
                    );


                  return (

                    <article
                      key={
                        workflowId
                      }
                      className="px-5 py-5 transition hover:bg-slate-50/70 sm:px-6"
                    >

                      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">

                        <div className="min-w-0">

                          <div className="flex items-center gap-3">

                            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">

                              <GitBranch
                                size={20}
                              />

                            </div>


                            <div className="min-w-0">

                              <h3 className="truncate text-base font-semibold text-slate-950">
                                {workflowName}
                              </h3>

                              <p className="mt-1 truncate text-xs text-slate-500">
                                Code: {workflowCode}
                              </p>

                            </div>

                          </div>


                          <div className="mt-4 flex flex-wrap gap-2">

                            <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-600">
                              Version {workflowVersion}
                            </span>

                            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-600">
                              {workflowStatus}
                            </span>

                          </div>

                        </div>


                        <div className="flex shrink-0 flex-wrap gap-2">

                          <button
                            type="button"
                            onClick={() =>
                              navigate(
                                `/workflows/${workflowId}`
                              )
                            }
                            className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
                          >

                            <ExternalLink
                              size={14}
                            />

                            Open workflow

                          </button>


                          <button
                            type="button"
                            disabled
                            title="Open the workflow before starting governed runtime execution."
                            className="inline-flex cursor-not-allowed items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-400"
                          >

                            <Play
                              size={14}
                            />

                            Run

                          </button>

                        </div>

                      </div>

                    </article>

                  );

                }
              )}

            </div>

          </section>

        )}

      </div>

    </div>
  );

}
