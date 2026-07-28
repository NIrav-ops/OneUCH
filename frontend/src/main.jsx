import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import "./index.css";

import AppLayout from "./layouts/AppLayout";

import Dashboard from "./pages/Dashboard";
import Inbox from "./pages/Inbox";
import ActionCenter from "./pages/ActionCenter";
import ApprovalCenter from "./pages/ApprovalCenter";
import SearchResults from "./pages/SearchResults";
import Notifications from "./pages/Notifications";
import Login from "./pages/Login";

function AppWrapper() {
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
          path="/actions"
          element={<ActionCenter />}
        />

        <Route
          path="/approvals"
          element={<ApprovalCenter />}
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

ReactDOM.createRoot(
  document.getElementById("root")
).render(
  <BrowserRouter>
    <AppWrapper />
  </BrowserRouter>
);