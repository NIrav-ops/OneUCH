import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";

import {
  AlertTriangle,
  Bell,
  Briefcase,
  CheckSquare2,
  Clock3,
  Command,
  GitBranch,
  Handshake,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  Scale,
  Search,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";

import axios from "../axiosConfig";

import {
  clearStoredAuthTokens,
} from "../authSession";


const NAVIGATION = [
  {
    label: "Workspace",
    items: [
      {
        to: "/dashboard",
        label: "Dashboard",
        icon: LayoutDashboard,
      },
      {
        to: "/inbox",
        label: "Inbox",
        icon: Mail,
      },
      {
        to: "/attention",
        label: "Attention Center",
        icon: AlertTriangle,
      },
      {
        to: "/my-work",
        label: "My Work",
        icon: Briefcase,
      },
    ],
  },
  {
    label: "Execution",
    items: [
      {
        to: "/actions",
        label: "Action Center",
        icon: CheckSquare2,
      },
      {
        to: "/approvals",
        label: "Approval Center",
        icon: ShieldCheck,
      },
      {
        to: "/commitments",
        label: "Commitments",
        icon: Handshake,
      },
      {
        to: "/waiting-for",
        label: "Waiting For",
        icon: Clock3,
      },
    ],
  },
  {
    label: "Intelligence",
    items: [
      {
        to: "/decisions",
        label: "Decisions",
        icon: Scale,
      },
      {
        to: "/relationships",
        label: "Relationships",
        icon: Users,
      },
      {
        to: "/workflows",
        label: "Workflows",
        icon: GitBranch,
      },
    ],
  },
  {
    label: "System",
    items: [
      {
        to: "/settings",
        label: "Settings",
        icon: Settings,
      },
    ],
  },
];


const PAGE_CONTEXT = [
  {
    match: (path) =>
      path.startsWith(
        "/dashboard"
      ),
    eyebrow: "Workspace",
    title: "Dashboard",
    description:
      "Communication intelligence at a glance.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/inbox"
      ),
    eyebrow: "Communication",
    title: "Unified Inbox",
    description:
      "Work across connected Gmail and Microsoft 365 mailboxes.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/attention"
      ),
    eyebrow: "Intelligence",
    title: "Attention Center",
    description:
      "See what needs intervention before work slips.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/my-work"
      ),
    eyebrow: "Execution",
    title: "My Work",
    description:
      "Your personal execution workspace.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/actions"
      ),
    eyebrow: "Execution",
    title: "Action Center",
    description:
      "Track actionable work extracted from communication.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/approvals"
      ),
    eyebrow: "Governance",
    title: "Approval Center",
    description:
      "Review decisions that require explicit approval.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/commitments"
      ),
    eyebrow: "Accountability",
    title: "Commitments",
    description:
      "Keep promises and ownership visible.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/waiting-for"
      ),
    eyebrow: "Accountability",
    title: "Waiting For",
    description:
      "Track external dependencies and expected responses.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/decisions"
      ),
    eyebrow: "Intelligence",
    title: "Decisions",
    description:
      "Maintain a durable record of communication-backed decisions.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/relationships"
      ),
    eyebrow: "Intelligence",
    title: "Relationships",
    description:
      "Understand the people and communication patterns around work.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/workflows"
      ),
    eyebrow: "Automation",
    title: "Workflows",
    description:
      "Turn governed communication into repeatable execution.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/settings"
      ),
    eyebrow: "System",
    title: "Settings",
    description:
      "Manage connected mailboxes and workspace configuration.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/notifications"
      ),
    eyebrow: "Workspace",
    title: "Notifications",
    description:
      "Review updates that need your attention.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/search"
      ),
    eyebrow: "Workspace",
    title: "Search",
    description:
      "Find communication and execution records across One UCH.",
  },
];


function ProductMark() {

  return (
    <div
      className="
        flex
        h-10
        w-10
        items-center
        justify-center
        rounded-xl
        bg-slate-950
        text-sm
        font-bold
        tracking-tight
        text-white
        shadow-sm
      "
      aria-hidden="true"
    >
      OU
    </div>
  );

}


export default function AppLayout() {

  const navigate = (
    useNavigate()
  );

  const location = (
    useLocation()
  );


  const [
    searchText,
    setSearchText,
  ] = useState("");


  const [
    unreadCount,
    setUnreadCount,
  ] = useState(0);


  const [
    sidebarOpen,
    setSidebarOpen,
  ] = useState(false);


  const [
    mobileSearchOpen,
    setMobileSearchOpen,
  ] = useState(false);


  const pageContext = (
    useMemo(
      () => {

        return (
          PAGE_CONTEXT.find(
            (item) =>
              item.match(
                location.pathname
              )
          )
          ||
          {
            eyebrow:
              "One UCH",

            title:
              "Communication Intelligence",

            description:
              "Communication, intelligence and execution in one workspace.",
          }
        );

      },
      [
        location.pathname,
      ]
    )
  );


  useEffect(
    () => {

      setSidebarOpen(
        false
      );

      setMobileSearchOpen(
        false
      );

    },
    [
      location.pathname,
    ]
  );


  useEffect(
    () => {

      let cancelled = (
        false
      );


      const loadNotifications =
        async () => {

          try {

            const response =
              await axios.get(
                "/api/notifications/"
              );


            if (!cancelled) {

              setUnreadCount(
                response.data
                  ?.unread_count
                ||
                0
              );

            }

          } catch (error) {

            if (!cancelled) {

              console.error(
                "Notification error:",
                error
              );

            }

          }

        };


      loadNotifications();


      return () => {

        cancelled = (
          true
        );

      };

    },
    []
  );


  const submitSearch =
    (event) => {

      event.preventDefault();


      const term = (
        searchText.trim()
      );


      if (!term) {
        return;
      }


      navigate(
        `/search?q=${encodeURIComponent(
          term
        )}`
      );


      setSearchText(
        ""
      );

      setMobileSearchOpen(
        false
      );

    };


  const logout = () => {

    clearStoredAuthTokens();

    window.location.replace(
      "/"
    );

  };


  const navLinkClass =
    ({
      isActive,
    }) => {

      const base =
        "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors";


      return (
        isActive
          ? (
              base
              +
              " bg-slate-950 text-white shadow-sm"
            )
          : (
              base
              +
              " text-slate-600 hover:bg-slate-100 hover:text-slate-950"
            )
      );

    };


  const sidebar = (
    <>
      <div
        className="
          flex
          h-[72px]
          items-center
          justify-between
          border-b
          border-slate-200
          px-4
        "
      >
        <div
          className="
            flex
            items-center
            gap-3
          "
        >
          <ProductMark />

          <div>
            <div
              className="
                text-sm
                font-semibold
                tracking-tight
                text-slate-950
              "
            >
              One UCH
            </div>

            <div
              className="
                text-[11px]
                font-medium
                uppercase
                tracking-[0.16em]
                text-slate-400
              "
            >
              Intelligence Layer
            </div>
          </div>
        </div>


        <button
          type="button"
          onClick={() =>
            setSidebarOpen(
              false
            )
          }
          className="
            rounded-lg
            p-2
            text-slate-500
            hover:bg-slate-100
            hover:text-slate-900
            lg:hidden
          "
          aria-label="Close navigation"
        >
          <X
            size={19}
          />
        </button>
      </div>


      <nav
        className="
          flex-1
          overflow-y-auto
          px-3
          py-4
        "
        aria-label="Primary navigation"
      >
        {
          NAVIGATION.map(
            (section) => (

              <div
                key={
                  section.label
                }
                className="mb-5"
              >
                <div
                  className="
                    mb-1.5
                    px-3
                    text-[10px]
                    font-semibold
                    uppercase
                    tracking-[0.18em]
                    text-slate-400
                  "
                >
                  {
                    section.label
                  }
                </div>


                <div
                  className="
                    space-y-1
                  "
                >
                  {
                    section.items.map(
                      (item) => {

                        const Icon = (
                          item.icon
                        );


                        return (
                          <NavLink
                            key={
                              item.to
                            }
                            to={
                              item.to
                            }
                            className={
                              navLinkClass
                            }
                          >
                            {
                              ({
                                isActive,
                              }) => (
                                <>
                                  <Icon
                                    size={18}
                                    strokeWidth={1.8}
                                    className={
                                      isActive
                                        ? "text-white"
                                        : "text-slate-400 group-hover:text-slate-700"
                                    }
                                  />

                                  <span>
                                    {
                                      item.label
                                    }
                                  </span>
                                </>
                              )
                            }
                          </NavLink>
                        );

                      }
                    )
                  }
                </div>
              </div>

            )
          )
        }
      </nav>


      <div
        className="
          border-t
          border-slate-200
          p-3
        "
      >
        <div
          className="
            rounded-xl
            bg-slate-50
            p-3
          "
        >
          <div
            className="
              mb-3
              flex
              items-center
              gap-2
            "
          >
            <div
              className="
                flex
                h-8
                w-8
                items-center
                justify-center
                rounded-lg
                bg-white
                text-[11px]
                font-bold
                text-slate-700
                shadow-sm
                ring-1
                ring-slate-200
              "
            >
              OU
            </div>

            <div
              className="
                min-w-0
              "
            >
              <div
                className="
                  truncate
                  text-xs
                  font-semibold
                  text-slate-800
                "
              >
                Secure workspace
              </div>

              <div
                className="
                  text-[11px]
                  text-slate-500
                "
              >
                Connected session
              </div>
            </div>
          </div>


          <button
            type="button"
            onClick={
              logout
            }
            className="
              flex
              w-full
              items-center
              justify-center
              gap-2
              rounded-lg
              border
              border-slate-200
              bg-white
              px-3
              py-2
              text-xs
              font-medium
              text-slate-600
              transition-colors
              hover:border-slate-300
              hover:text-slate-950
            "
          >
            <LogOut
              size={15}
            />

            Sign out
          </button>
        </div>
      </div>
    </>
  );


  return (
    <div
      className="
        min-h-screen
        bg-slate-50
        text-slate-950
      "
    >

      {/* Mobile backdrop */}
      {
        sidebarOpen && (
          <button
            type="button"
            className="
              fixed
              inset-0
              z-40
              bg-slate-950/30
              backdrop-blur-[1px]
              lg:hidden
            "
            onClick={() =>
              setSidebarOpen(
                false
              )
            }
            aria-label="Close navigation"
          />
        )
      }


      {/* Mobile sidebar */}
      <aside
        className={`
          fixed
          inset-y-0
          left-0
          z-50
          flex
          w-72
          flex-col
          border-r
          border-slate-200
          bg-white
          shadow-2xl
          transition-transform
          duration-200
          lg:hidden
          ${
            sidebarOpen
              ? "translate-x-0"
              : "-translate-x-full"
          }
        `}
      >
        {
          sidebar
        }
      </aside>


      <div
        className="
          flex
          min-h-screen
        "
      >

        {/* Desktop sidebar */}
        <aside
          className="
            sticky
            top-0
            hidden
            h-screen
            w-72
            shrink-0
            flex-col
            border-r
            border-slate-200
            bg-white
            lg:flex
          "
        >
          {
            sidebar
          }
        </aside>


        <div
          className="
            flex
            min-w-0
            flex-1
            flex-col
          "
        >

          {/* Premium application header */}
          <header
            className="
              sticky
              top-0
              z-30
              border-b
              border-slate-200/90
              bg-white/95
              backdrop-blur
            "
          >
            <div
              className="
                flex
                min-h-[72px]
                items-center
                gap-3
                px-4
                sm:px-6
              "
            >

              <button
                type="button"
                onClick={() =>
                  setSidebarOpen(
                    true
                  )
                }
                className="
                  rounded-xl
                  border
                  border-slate-200
                  bg-white
                  p-2.5
                  text-slate-600
                  shadow-sm
                  hover:bg-slate-50
                  lg:hidden
                "
                aria-label="Open navigation"
              >
                <Menu
                  size={19}
                />
              </button>


              <div
                className="
                  min-w-0
                  flex-1
                "
              >
                <div
                  className="
                    hidden
                    text-[10px]
                    font-semibold
                    uppercase
                    tracking-[0.18em]
                    text-slate-400
                    sm:block
                  "
                >
                  {
                    pageContext.eyebrow
                  }
                </div>

                <div
                  className="
                    truncate
                    text-base
                    font-semibold
                    tracking-tight
                    text-slate-950
                  "
                >
                  {
                    pageContext.title
                  }
                </div>
              </div>


              <form
                onSubmit={
                  submitSearch
                }
                className="
                  hidden
                  w-full
                  max-w-md
                  items-center
                  md:flex
                "
              >
                <div
                  className="
                    flex
                    w-full
                    items-center
                    gap-2.5
                    rounded-xl
                    border
                    border-slate-200
                    bg-slate-50
                    px-3.5
                    py-2.5
                    transition
                    focus-within:border-slate-300
                    focus-within:bg-white
                    focus-within:shadow-sm
                  "
                >
                  <Search
                    size={17}
                    className="
                      shrink-0
                      text-slate-400
                    "
                  />

                  <input
                    value={
                      searchText
                    }
                    onChange={
                      (event) =>
                        setSearchText(
                          event.target.value
                        )
                    }
                    placeholder="Search One UCH"
                    className="
                      min-w-0
                      flex-1
                      bg-transparent
                      text-sm
                      text-slate-800
                      outline-none
                      placeholder:text-slate-400
                    "
                  />

                  <div
                    className="
                      hidden
                      items-center
                      gap-1
                      rounded-md
                      border
                      border-slate-200
                      bg-white
                      px-1.5
                      py-0.5
                      text-[10px]
                      font-medium
                      text-slate-400
                      xl:flex
                    "
                  >
                    <Command
                      size={10}
                    />

                    Search
                  </div>
                </div>
              </form>


              <button
                type="button"
                onClick={() =>
                  setMobileSearchOpen(
                    (current) =>
                      !current
                  )
                }
                className="
                  rounded-xl
                  border
                  border-slate-200
                  bg-white
                  p-2.5
                  text-slate-600
                  shadow-sm
                  hover:bg-slate-50
                  md:hidden
                "
                aria-label="Search"
              >
                <Search
                  size={18}
                />
              </button>


              <button
                type="button"
                onClick={() =>
                  navigate(
                    "/notifications"
                  )
                }
                className="
                  relative
                  rounded-xl
                  border
                  border-slate-200
                  bg-white
                  p-2.5
                  text-slate-600
                  shadow-sm
                  hover:bg-slate-50
                  hover:text-slate-950
                "
                aria-label="Notifications"
              >
                <Bell
                  size={18}
                />

                {
                  unreadCount > 0 && (
                    <span
                      className="
                        absolute
                        -right-1.5
                        -top-1.5
                        flex
                        min-h-[18px]
                        min-w-[18px]
                        items-center
                        justify-center
                        rounded-full
                        bg-rose-600
                        px-1
                        text-[9px]
                        font-bold
                        text-white
                        ring-2
                        ring-white
                      "
                    >
                      {
                        unreadCount > 99
                          ? "99+"
                          : unreadCount
                      }
                    </span>
                  )
                }
              </button>
            </div>


            {
              mobileSearchOpen && (
                <form
                  onSubmit={
                    submitSearch
                  }
                  className="
                    border-t
                    border-slate-100
                    px-4
                    py-3
                    md:hidden
                  "
                >
                  <div
                    className="
                      flex
                      items-center
                      gap-2
                      rounded-xl
                      border
                      border-slate-200
                      bg-slate-50
                      px-3
                      py-2.5
                    "
                  >
                    <Search
                      size={16}
                      className="text-slate-400"
                    />

                    <input
                      autoFocus
                      value={
                        searchText
                      }
                      onChange={
                        (event) =>
                          setSearchText(
                            event.target.value
                          )
                      }
                      placeholder="Search emails, actions, approvals..."
                      className="
                        min-w-0
                        flex-1
                        bg-transparent
                        text-sm
                        outline-none
                      "
                    />
                  </div>
                </form>
              )
            }
          </header>


          <div
            className="
              border-b
              border-slate-100
              bg-white
              px-4
              py-3
              sm:px-6
            "
          >
            <p
              className="
                max-w-4xl
                text-xs
                leading-5
                text-slate-500
                sm:text-sm
              "
            >
              {
                pageContext.description
              }
            </p>
          </div>


          <main
            className="
              min-w-0
              flex-1
              overflow-x-hidden
            "
          >
            <Outlet />
          </main>

        </div>
      </div>
    </div>
  );

}
