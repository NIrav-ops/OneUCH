import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
  useSearchParams,
} from "react-router-dom";

import axios from "../axiosConfig";


export default function SearchResults() {

  const navigate =
    useNavigate();


  const [
    params,
    setParams,
  ] = useSearchParams();


  const q =
    params.get(
      "q"
    ) ||
    "";


  const [
    query,
    setQuery,
  ] = useState(q);


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  const [
    results,
    setResults,
  ] = useState([]);


  const [
    grouped,
    setGrouped,
  ] = useState({
    messages: [],
    actions: [],
    approvals: [],
    followups: [],
  });


  const fetchSearch =
    async (
      searchTerm
    ) => {

      const term =
        searchTerm.trim();


      if (!term) {

        setResults(
          []
        );

        setGrouped({
          messages:
            [],
          actions:
            [],
          approvals:
            [],
          followups:
            [],
        });

        return;

      }


      try {

        setLoading(
          true
        );

        setError(
          ""
        );


        const res =
          await axios.get(
            `/api/search/?q=${encodeURIComponent(
              term
            )}`
          );


        setResults(
          Array.isArray(
            res.data?.results
          )
            ? res.data.results
            : []
        );


        setGrouped(
          res.data?.grouped ||
          {
            messages:
              [],
            actions:
              [],
            approvals:
              [],
            followups:
              [],
          }
        );

      } catch (err) {

        console.error(
          "Search error:",
          err
        );


        setError(
          "Unable to search right now."
        );

      } finally {

        setLoading(
          false
        );

      }

    };


  useEffect(
    () => {

      setQuery(
        q
      );

      fetchSearch(
        q
      );

    },
    [
      q,
    ]
  );


  const handleSubmit =
    (
      event
    ) => {

      event.preventDefault();


      const term =
        query.trim();


      if (!term) {
        return;
      }


      setParams({
        q:
          term,
      });

    };


  const sections =
    useMemo(
      () => [
        {
          key:
            "messages",
          title:
            "Inbox Messages",
          items:
            grouped.messages,
        },
        {
          key:
            "actions",
          title:
            "Actions",
          items:
            grouped.actions,
        },
        {
          key:
            "approvals",
          title:
            "Approvals",
          items:
            grouped.approvals,
        },
        {
          key:
            "followups",
          title:
            "Follow-ups",
          items:
            grouped.followups,
        },
      ],
      [
        grouped,
      ]
    );


  return (
    <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

      <div className="mx-auto max-w-[1540px]">


        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 text-white shadow-sm">

          <div className="absolute right-0 top-0 h-56 w-56 rounded-full bg-indigo-500/10 blur-3xl" />

          <div className="relative px-6 py-7 lg:px-8 lg:py-8">

            <div className="max-w-3xl">

              <div className="inline-flex rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.17em] text-slate-300">
                Cross-workspace discovery
              </div>

              <h1 className="mt-5 text-3xl font-semibold tracking-tight lg:text-4xl">
                Search
              </h1>

              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                Find communication, actions, approvals and follow-ups without switching between execution surfaces.
              </p>

            </div>


            <form
              onSubmit={
                handleSubmit
              }
              className="mt-6 flex max-w-3xl flex-col gap-2 sm:flex-row"
            >

              <input
                value={
                  query
                }
                onChange={
                  (event) =>
                    setQuery(
                      event.target.value
                    )
                }
                placeholder="Search emails, actions, approvals and follow-ups..."
                className="min-w-0 flex-1 rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-400 focus:border-white/30 focus:bg-white/15"
              />


              <button
                type="submit"
                className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-slate-950 shadow-sm hover:bg-slate-100"
              >
                Search workspace
              </button>

            </form>

          </div>

        </section>


        {error && (

          <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-700">
            {error}
          </div>

        )}


        <section className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
              Total results
            </p>

            <p className="mt-2 text-2xl font-semibold text-slate-950">
              {results.length}
            </p>

          </div>


          {sections.map(
            (section) => (

              <div
                key={
                  section.key
                }
                className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
              >

                <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                  {section.title}
                </p>

                <p className="mt-2 text-2xl font-semibold text-slate-950">
                  {section.items.length}
                </p>

              </div>

            )
          )}

        </section>


        {!q &&
          !loading ? (

          <section className="mt-5 rounded-[26px] border border-dashed border-slate-300 bg-white px-6 py-16 text-center shadow-sm">

            <p className="text-sm font-semibold text-slate-700">
              Search the One UCH workspace
            </p>

            <p className="mt-2 text-xs text-slate-400">
              Enter a term above to search communication and execution records.
            </p>

          </section>

        ) : loading ? (

          <section className="mt-5 rounded-[26px] border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">

            <div className="mx-auto h-8 w-8 animate-pulse rounded-full bg-slate-200" />

            <p className="mt-4 text-sm font-medium text-slate-500">
              Searching workspace...
            </p>

          </section>

        ) : (

          <div className="mt-5 grid gap-5 xl:grid-cols-2">

            {sections.map(
              (section) => (

                <section
                  key={
                    section.key
                  }
                  className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm"
                >

                  <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">

                    <h2 className="text-base font-semibold text-slate-950">
                      {section.title}
                    </h2>

                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                      {section.items.length}
                    </span>

                  </div>


                  {section.items.length ===
                  0 ? (

                    <div className="px-5 py-10 text-center text-xs text-slate-400">
                      No {section.title.toLowerCase()} found.
                    </div>

                  ) : (

                    <div className="divide-y divide-slate-100">

                      {section.items.map(
                        (item) => (

                          <button
                            type="button"
                            key={`${section.key}-${item.id}`}
                            onClick={() =>
                              navigate(
                                item.url ||
                                "/dashboard"
                              )
                            }
                            className="block w-full px-5 py-4 text-left transition hover:bg-slate-50"
                          >

                            <div className="flex items-start justify-between gap-3">

                              <div className="min-w-0">

                                <h3 className="truncate text-sm font-semibold text-slate-900">
                                  {item.title ||
                                    "Untitled result"}
                                </h3>

                                {item.subtitle && (

                                  <p className="mt-1 truncate text-xs text-slate-500">
                                    {item.subtitle}
                                  </p>

                                )}


                                {item.preview && (

                                  <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">
                                    {item.preview}
                                  </p>

                                )}

                              </div>


                              <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-500">
                                {item.type ||
                                  section.key}
                              </span>

                            </div>

                          </button>

                        )
                      )}

                    </div>

                  )}

                </section>

              )
            )}

          </div>

        )}


        <div className="mt-5">

          <button
            type="button"
            onClick={() =>
              navigate(
                "/dashboard"
              )
            }
            className="text-xs font-semibold text-slate-500 hover:text-slate-950"
          >
            ? Back to Dashboard
          </button>

        </div>

      </div>

    </div>
  );

}
