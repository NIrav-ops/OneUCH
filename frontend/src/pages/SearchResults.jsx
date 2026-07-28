import { useEffect, useMemo, useState } from "react";
import axios from "../axiosConfig";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function SearchResults() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";

  const [query, setQuery] = useState(q);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [grouped, setGrouped] = useState({
    messages: [],
    actions: [],
    approvals: [],
    followups: [],
  });

  const fetchSearch = async (searchTerm) => {
    const term = searchTerm.trim();

    if (!term) {
      setResults([]);
      setGrouped({
        messages: [],
        actions: [],
        approvals: [],
        followups: [],
      });
      return;
    }

    try {
      setLoading(true);
      setError("");

      const res = await axios.get(`/api/search/?q=${encodeURIComponent(term)}`);
      setResults(Array.isArray(res.data?.results) ? res.data.results : []);
      setGrouped(
        res.data?.grouped || {
          messages: [],
          actions: [],
          approvals: [],
          followups: [],
        }
      );
    } catch (err) {
      console.error("Search error:", err);
      setError("Unable to search right now.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setQuery(q);
    fetchSearch(q);
  }, [q]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const term = query.trim();
    if (!term) return;
    setParams({ q: term });
  };

  const sections = useMemo(
    () => [
      { key: "messages", title: "Inbox Messages", items: grouped.messages },
      { key: "actions", title: "Actions", items: grouped.actions },
      { key: "approvals", title: "Approvals", items: grouped.approvals },
      { key: "followups", title: "Follow-ups", items: grouped.followups },
    ],
    [grouped]
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Search</h1>
            <p className="mt-1 text-sm text-slate-600">
              Search across messages, actions, approvals, and follow-ups.
            </p>
          </div>

          <button
            onClick={() => navigate("/dashboard")}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-100"
          >
            Back to Dashboard
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mb-6">
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search emails, actions, approvals..."
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-500"
            />
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800"
            >
              Search
            </button>
          </div>
        </form>

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!query && !loading && (
          <div className="rounded-2xl bg-white p-6 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
            Type something to search.
          </div>
        )}

        {loading ? (
          <div className="rounded-2xl bg-white p-6 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
            Searching...
          </div>
        ) : (
          <div className="space-y-6">
            <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
              <div className="text-sm text-slate-500">Total Results</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{results.length}</div>
            </div>

            {sections.map((section) => (
              <div
                key={section.key}
                className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200"
              >
                <div className="border-b border-slate-200 px-5 py-4">
                  <h2 className="text-lg font-semibold text-slate-900">{section.title}</h2>
                </div>

                <div className="divide-y divide-slate-200">
                  {section.items.length === 0 ? (
                    <div className="px-5 py-8 text-sm text-slate-500">
                      No {section.title.toLowerCase()} found.
                    </div>
                  ) : (
                    section.items.map((item) => (
                      <button
                        key={`${section.key}-${item.id}`}
                        onClick={() => navigate(item.url || "/dashboard")}
                        className="block w-full px-5 py-4 text-left hover:bg-slate-50"
                      >
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-semibold text-slate-900">
                            {item.title}
                          </h3>
                          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                            {item.type}
                          </span>
                        </div>

                        <div className="mt-1 text-sm text-slate-500">
                          {item.subtitle}
                        </div>

                        {item.preview && (
                          <div className="mt-2 text-sm text-slate-600">
                            {item.preview}
                          </div>
                        )}
                      </button>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}