import {
  useEffect,
  useState,
} from "react";

import {
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import {
  bootstrapBrowserSession,
} from "./axiosConfig";

import AppLayout from "./layouts/AppLayout";

import Dashboard from "./pages/Dashboard";
import Inbox from "./pages/Inbox";
import ActionCenter from "./pages/ActionCenter";
import AttentionCenter from "./pages/AttentionCenter";
import MyWork from "./pages/MyWork";
import Commitments from "./pages/Commitments";
import WaitingFor from "./pages/WaitingFor";
import Decisions from "./pages/Decisions";
import Relationships from "./pages/Relationships";
import Settings from "./pages/Settings";
import ApprovalCenter from "./pages/ApprovalCenter";
import SearchResults from "./pages/SearchResults";
import Notifications from "./pages/Notifications";
import Login from "./pages/Login";
import Workflows from "./pages/Workflows";
import WorkflowDetail from "./pages/WorkflowDetail";
import WorkflowRuntime from "./pages/WorkflowRuntime";


export default function App() {

  const [
    sessionState,
    setSessionState,
  ] = useState(
    "bootstrapping"
  );


  useEffect(
    () => {

      let active =
        true;


      const timer =
        window.setTimeout(
          () => {

            void (
              bootstrapBrowserSession()
                .then(
                  (authenticated) => {

                    if (active) {

                      setSessionState(
                        authenticated
                          ? "authenticated"
                          : "anonymous"
                      );

                    }

                  }
                )
                .catch(
                  () => {

                    if (active) {

                      setSessionState(
                        "anonymous"
                      );

                    }

                  }
                )
            );

          },
          0
        );


      return () => {

        active =
          false;

        window.clearTimeout(
          timer
        );

      };

    },
    []
  );


  if (
    sessionState ===
    "bootstrapping"
  ) {

    return (
      <div
        className="
          flex
          min-h-screen
          items-center
          justify-center
          bg-slate-950
          text-sm
          font-medium
          text-slate-300
        "
      >
        Securing your One UCH session...
      </div>
    );

  }


  if (
    sessionState !==
    "authenticated"
  ) {

    return (
      <Login
        onLogin={() =>
          setSessionState(
            "authenticated"
          )
        }
      />
    );

  }


  return (
    <Routes>
      <Route element={<AppLayout />}>

        <Route
          path="/dashboard"
          element={<Dashboard />}
        />

        <Route
          path="/inbox"
          element={<Inbox />}
        />

        <Route
          path="/attention"
          element={<AttentionCenter />}
        />

        <Route
          path="/my-work"
          element={<MyWork />}
        />

        <Route
          path="/commitments"
          element={<Commitments />}
        />

        <Route
          path="/waiting-for"
          element={<WaitingFor />}
        />

        <Route
          path="/decisions"
          element={<Decisions />}
        />

        <Route
          path="/relationships"
          element={<Relationships />}
        />

        <Route
          path="/settings"
          element={<Settings />}
        />

        <Route
          path="/actions"
          element={<ActionCenter />}
        />

        <Route
          path="/approvals"
          element={<ApprovalCenter />}
        />

        <Route
          path="/workflows"
          element={<Workflows />}
        />

        <Route
          path="/workflows/:workflowId"
          element={<WorkflowDetail />}
        />

        <Route
          path="/workflows/:workflowId/runtime/:instanceId"
          element={<WorkflowRuntime />}
        />

        <Route
          path="/search"
          element={<SearchResults />}
        />

        <Route
          path="/notifications"
          element={<Notifications />}
        />

        <Route
          path="*"
          element={
            <Navigate
              to="/dashboard"
              replace
            />
          }
        />

      </Route>
    </Routes>
  );

}
