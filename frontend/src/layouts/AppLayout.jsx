import { useState, useEffect } from "react";
import { useNavigate, NavLink, Outlet } from "react-router-dom";
import axios from "../axiosConfig";

import {
  Mail,
  Settings,
  LayoutDashboard,
  AlertTriangle,
  Briefcase,
  Handshake,
  Clock,
  Scale,
  Users,
  CheckSquare,
  ShieldCheck,
  Search,
  Bell,
  GitBranch,
} from "lucide-react";

export default function AppLayout() {
  const navigate = useNavigate();

  const [searchText, setSearchText] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const loadNotifications = async () => {
      try {
        const res = await axios.get(
          "/api/notifications/"
        );

        if (!cancelled) {
          setUnreadCount(
            res.data?.unread_count || 0
          );
        }
      } catch (err) {
        if (!cancelled) {
          console.error(
            "Notification error:",
            err
          );
        }
      }
    };

    loadNotifications();

    return () => {
      cancelled = true;
    };
  }, []);

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-3 py-2 rounded ${
      isActive ? "bg-gray-100 font-medium" : "hover:bg-gray-100"
    }`;

  const submitSearch = (e) => {
    e.preventDefault();

    const term = searchText.trim();

    if (!term) return;

    navigate(`/search?q=${encodeURIComponent(term)}`);

    setSearchText("");
  };

  return (
    <div className="h-screen flex bg-gray-100 text-gray-800">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r flex flex-col">
        <div className="p-6 text-xl font-semibold border-b">
          One UCH
        </div>

        <nav className="flex-1 p-4 space-y-1 text-sm">
          <NavLink to="/dashboard" className={linkClass}>
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>

          <NavLink to="/attention" className={linkClass}>
            <AlertTriangle size={18} />
            Attention Center
          </NavLink>

          <NavLink to="/my-work" className={linkClass}>
            <Briefcase size={18} />
            My Work
          </NavLink>

          <NavLink to="/commitments" className={linkClass}>
            <Handshake size={18} />
            Commitments
          </NavLink>

          <NavLink to="/waiting-for" className={linkClass}>
            <Clock size={18} />
            Waiting For
          </NavLink>

          <NavLink to="/decisions" className={linkClass}>
            <Scale size={18} />
            Decisions
          </NavLink>

          <NavLink to="/relationships" className={linkClass}>
            <Users size={18} />
            Relationships
          </NavLink>

          <NavLink to="/inbox" className={linkClass}>
            <Mail size={18} />
            Inbox
          </NavLink>

          <NavLink to="/actions" className={linkClass}>
            <CheckSquare size={18} />
            Action Center
          </NavLink>

          <NavLink to="/approvals" className={linkClass}>
            <ShieldCheck size={18} />
            Approval Center
          </NavLink>

          <NavLink to="/workflows" className={linkClass}>
            <GitBranch size={18} />
            Workflows
          </NavLink>

          <NavLink to="/settings" className={linkClass}>
            <Settings size={18} />
            Settings
          </NavLink>
        </nav>
      </div>

      {/* Main Area */}
      <div className="flex-1 flex flex-col overflow-auto">

        {/* Top Bar */}
        <div className="border-b bg-white px-4 py-3 flex items-center gap-3">

          {/* Search */}
          <form
            onSubmit={submitSearch}
            className="flex flex-1 gap-2"
          >
            <div className="flex flex-1 items-center gap-2 rounded-xl border border-slate-300 bg-slate-50 px-3 py-2">
              <Search
                size={16}
                className="text-slate-500"
              />

              <input
                value={searchText}
                onChange={(e) =>
                  setSearchText(e.target.value)
                }
                placeholder="Search emails, actions, approvals..."
                className="w-full bg-transparent text-sm outline-none"
              />
            </div>

            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              Search
            </button>
          </form>

          {/* Notification Bell */}
          <button
            onClick={() => navigate("/notifications")}
            className="relative p-2 rounded-lg hover:bg-gray-100"
          >
            <Bell size={22} />

            {unreadCount > 0 && (
              <span
                className="
                  absolute
                  -top-1
                  -right-1
                  bg-red-500
                  text-white
                  text-xs
                  rounded-full
                  min-w-[18px]
                  h-[18px]
                  flex
                  items-center
                  justify-center
                "
              >
                {unreadCount}
              </span>
            )}
          </button>

        </div>

        <Outlet />
      </div>
    </div>
  );
}