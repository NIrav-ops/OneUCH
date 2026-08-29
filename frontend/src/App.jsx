import { useState } from "react";
import {
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import AppLayout from "./layouts/AppLayout";

import Dashboard from "./pages/Dashboard";
import Inbox from "./pages/Inbox";
import ActionCenter from "./pages/ActionCenter";
import AttentionCenter from "./pages/AttentionCenter";
import MyWork from "./pages/MyWork";
import ApprovalCenter from "./pages/ApprovalCenter";
import SearchResults from "./pages/SearchResults";
import Notifications from "./pages/Notifications";
import Login from "./pages/Login";
import Workflows from "./pages/Workflows";
import WorkflowDetail from "./pages/WorkflowDetail";
import WorkflowRuntime from "./pages/WorkflowRuntime";

export default function App() {
  const [isAuth, setIsAuth] = useState(
    !!localStorage.getItem("access")
  );

  if (!isAuth) {
    return (
      <Login
        onLogin={() => setIsAuth(true)}
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