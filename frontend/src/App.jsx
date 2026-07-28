import { useState } from "react";
import Inbox from "./pages/Inbox";
import ActionCenter from "./pages/ActionCenter";

export default function App() {
  const [view, setView] = useState("inbox");

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">One UCH</h1>
          <p className="text-xs text-slate-500">
            Communication intelligence and execution layer
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setView("inbox")}
            className={`rounded-xl px-4 py-2 text-sm font-medium ${
              view === "inbox"
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Inbox
          </button>

          <button
            onClick={() => setView("actions")}
            className={`rounded-xl px-4 py-2 text-sm font-medium ${
              view === "actions"
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Action Center
          </button>
        </div>
      </div>

      {view === "inbox" ? <Inbox /> : <ActionCenter />}
    </div>
  );
}