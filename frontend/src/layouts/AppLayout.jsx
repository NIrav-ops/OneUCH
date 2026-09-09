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
  CircleHelp,
  CheckSquare2,
  Clock3,
  Command,
  GitBranch,
  Handshake,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Scale,
  Search,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";

import axios, {
  endBrowserSession,
} from "../axiosConfig";


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
      "Execution priorities, decisions and response obligations at a glance.",
  },
  {
    match: (path) =>
      path.startsWith(
        "/inbox"
      ),
    eyebrow: "Communication",
    title: "Unified Inbox",
    description:
      "Work across all connected One UCH mailboxes.",
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

const PAGE_GUIDANCE = {
  "/dashboard": {
    useWhen:
      "Start here when you want the fastest view of what requires attention or execution now.",
    actions: [
      "Review active Actions and Approvals",
      "See work due today or already overdue",
      "Check follow-ups, escalations and SLA health",
      "Jump into Inbox or Attention Center",
    ],
    flow:
      "Dashboard is the command layer above communication, decisions and execution.",
  },

  "/inbox": {
    useWhen:
      "Use this page when you need the original communication context or need to respond from a connected mailbox.",
    actions: [
      "Read communication across connected mailboxes",
      "Search Inbox, Sent and Drafts",
      "Reply, Reply All or Forward",
      "Review the execution trail beside a conversation",
    ],
    flow:
      "Inbox provides communication context. One UCH turns that context into governed Actions, Approvals and follow-ups.",
  },

  "/attention": {
    useWhen:
      "Use this page when work may slip, needs intervention or has crossed a risk boundary.",
    actions: [
      "Review overdue or escalated work",
      "Identify SLA warnings and breaches",
      "Open the responsible work item",
    ],
    flow:
      "Attention Center highlights exceptions while execution remains in the underlying work page.",
  },

  "/my-work": {
    useWhen:
      "Use this page for execution responsibilities assigned to you.",
    actions: [
      "Review assigned work",
      "Prioritize due and overdue responsibilities",
      "Open the underlying execution item",
    ],
    flow:
      "My Work is your personal view of the wider One UCH execution model.",
  },

  "/actions": {
    useWhen:
      "Use this page when communication has become owned work requiring a responsible person, due date and lifecycle.",
    actions: [
      "Review active Actions",
      "Assign ownership and due dates",
      "Complete, ignore, reopen or snooze governed work",
      "Review suggestions before promoting them",
    ],
    flow:
      "Action Center converts communication into accountable execution while keeping suggestions human governed.",
  },

  "/approvals": {
    useWhen:
      "Use this page when a business request needs an explicit human decision before work proceeds.",
    actions: [
      "Review active Approvals",
      "Assign a reviewer",
      "Approve, reject or request more information",
      "Preserve decision rationale",
    ],
    flow:
      "Approval Center is the human-governance gate between communication and execution.",
  },

  "/commitments": {
    useWhen:
      "Use this page to keep communication-backed promises and obligations visible.",
    actions: [
      "Review commitments",
      "Track ownership and expected completion",
      "Open supporting communication",
    ],
    flow:
      "Commitments keep promises accountable even before they become formal Actions.",
  },

  "/waiting-for": {
    useWhen:
      "Use this page when progress depends on somebody else's response or action.",
    actions: [
      "Track expected responses",
      "Review follow-up obligations",
      "Open related communication",
    ],
    flow:
      "Waiting For separates external dependencies from work you directly own.",
  },

  "/decisions": {
    useWhen:
      "Use this page when you need the durable record of what was decided and why.",
    actions: [
      "Review communication-backed decisions",
      "Trace decision context",
      "Use previous decisions as organizational knowledge",
    ],
    flow:
      "Decisions preserve outcomes after immediate approval work is complete.",
  },

  "/relationships": {
    useWhen:
      "Use this page when people, roles and communication patterns matter to understanding work.",
    actions: [
      "Review relationship context",
      "Understand communication patterns",
      "Connect people to business activity",
    ],
    flow:
      "Relationships provide organizational context around communication and execution.",
  },

  "/workflows": {
    useWhen:
      "Use this page when a repeated business process should become governed execution.",
    actions: [
      "Review workflow definitions",
      "Inspect execution paths",
      "Review workflow runtime and history",
    ],
    flow:
      "Workflows turn repeated communication-driven processes into deterministic execution.",
  },

  "/settings": {
    useWhen:
      "Use this page to configure the workspace and connected communication accounts.",
    actions: [
      "Manage connected mailboxes",
      "Review workspace configuration",
      "Control supported communication settings",
    ],
    flow:
      "Settings configures One UCH while operational work remains in execution pages.",
  },

  "/notifications": {
    useWhen:
      "Use this page to review recent One UCH updates that may need your attention.",
    actions: [
      "Review notifications",
      "Open the related work or communication",
    ],
    flow:
      "Notifications point toward activity; the underlying page remains the source of truth.",
  },

  "/search": {
    useWhen:
      "Use this page when you know what you are looking for but not where it lives in One UCH.",
    actions: [
      "Search communication and execution records",
      "Open the matching source item",
    ],
    flow:
      "Search crosses modules while every result remains governed by its source page.",
  },
};



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


  const [
    desktopSidebarCollapsed,
    setDesktopSidebarCollapsed,
  ] = useState(
    () =>
      window.localStorage.getItem(
        "oneuch_sidebar_collapsed"
      ) === "true"
  );


  const [
    helpOpen,
    setHelpOpen,
  ] = useState(false);


  useEffect(
    () => {

      window.localStorage.setItem(
        "oneuch_sidebar_collapsed",
        desktopSidebarCollapsed
          ? "true"
          : "false"
      );

    },
    [
      desktopSidebarCollapsed,
    ]
  );


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


  const pageHelp = (
    useMemo(
      () => {

        const match = (
          Object.entries(
            PAGE_GUIDANCE
          ).find(
            (
              [
                path,
              ]
            ) =>
              location.pathname.startsWith(
                path
              )
          )
        );

        return (
          match?.[1]
          ||
          {
            useWhen:
              "Use this page to work with the current One UCH capability.",
            actions: [
              "Review the information shown here",
              "Open the underlying communication or execution item when needed",
            ],
            flow:
              "One UCH connects communication, intelligence, governance and execution in one workspace.",
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


  const logout =
    async () => {

      try {

        await endBrowserSession();

        window.location.replace(
          "/login"
        );

      } catch (error) {

        console.error(
          "Sign out failed:",
          error
        );

      }

    };


  const navLinkClass =
    ({
      isActive,
    }) => {

      const base =
        (
          "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors"
          +
          (
            desktopSidebarCollapsed
              ? " lg:justify-center lg:px-2"
              : ""
          )
        );


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
          h-[60px]
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

          <div
            className={
              desktopSidebarCollapsed
                ? "lg:hidden"
                : ""
            }
          >
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
                  className={`mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 ${
                    desktopSidebarCollapsed
                      ? "lg:hidden"
                      : ""
                  }`}
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
                            title={
                              desktopSidebarCollapsed
                                ? item.label
                                : undefined
                            }
                            aria-label={
                              desktopSidebarCollapsed
                                ? item.label
                                : undefined
                            }
                            onClick={() => {
                              setSidebarOpen(
                                false
                              );

                              setMobileSearchOpen(
                                false
                              );
                            }}
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

                                  <span
                                    className={
                                      desktopSidebarCollapsed
                                        ? "lg:hidden"
                                        : ""
                                    }
                                  >
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
              className={
                desktopSidebarCollapsed
                  ? "min-w-0 lg:hidden"
                  : "min-w-0"
              }
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

            <span
              className={
                desktopSidebarCollapsed
                  ? "lg:hidden"
                  : ""
              }
            >
              Sign out
            </span>
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




      {
        helpOpen && (
          <>
            <button
              type="button"
              className="
                fixed
                inset-0
                z-50
                bg-slate-950/25
                backdrop-blur-[1px]
              "
              onClick={() =>
                setHelpOpen(
                  false
                )
              }
              aria-label="Close page help"
            />

            <aside
              className="
                fixed
                inset-y-0
                right-0
                z-[60]
                flex
                w-full
                max-w-md
                flex-col
                border-l
                border-slate-200
                bg-white
                shadow-2xl
              "
              aria-label="Page help"
            >

              <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-5">

                <div>

                  <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                    <CircleHelp size={15} />
                    One UCH guide
                  </div>

                  <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
                    {pageContext.title}
                  </h2>

                </div>


                <button
                  type="button"
                  onClick={() =>
                    setHelpOpen(
                      false
                    )
                  }
                  className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 hover:bg-slate-50 hover:text-slate-950"
                  aria-label="Close help"
                >
                  <X size={18} />
                </button>

              </div>


              <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">

                <section className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">

                  <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                    What is this page for?
                  </p>

                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {pageContext.description}
                  </p>

                </section>


                <section>

                  <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                    When should I use it?
                  </p>

                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {pageHelp.useWhen}
                  </p>

                </section>


                <section>

                  <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                    What can I do here?
                  </p>

                  <div className="mt-3 space-y-2">

                    {pageHelp.actions.map(
                      (
                        action,
                        index
                      ) => (

                        <div
                          key={action}
                          className="flex gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5"
                        >

                          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-950 text-[9px] font-bold text-white">
                            {index + 1}
                          </span>

                          <span className="text-xs leading-5 text-slate-600">
                            {action}
                          </span>

                        </div>

                      )
                    )}

                  </div>

                </section>


                <section className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-4">

                  <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-indigo-500">
                    How it fits into One UCH
                  </p>

                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {pageHelp.flow}
                  </p>

                </section>

              </div>

            </aside>
          </>
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
          className={`
            sticky
            top-0
            hidden
            h-screen
            shrink-0
            flex-col
            border-r
            border-slate-200
            bg-white
            transition-[width]
            duration-200
            lg:flex
            ${
              desktopSidebarCollapsed
                ? "w-20"
                : "w-72"
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
                min-h-[60px]
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


              <button
                type="button"
                onClick={() =>
                  setDesktopSidebarCollapsed(
                    (current) =>
                      !current
                  )
                }
                className="
                  hidden
                  rounded-xl
                  border
                  border-slate-200
                  bg-white
                  p-2
                  text-slate-600
                  shadow-sm
                  hover:bg-slate-50
                  hover:text-slate-950
                  lg:inline-flex
                "
                aria-label={
                  desktopSidebarCollapsed
                    ? "Expand navigation"
                    : "Collapse navigation"
                }
                title={
                  desktopSidebarCollapsed
                    ? "Expand navigation"
                    : "Collapse navigation"
                }
              >
                {
                  desktopSidebarCollapsed
                    ? (
                      <PanelLeftOpen
                        size={18}
                      />
                    )
                    : (
                      <PanelLeftClose
                        size={18}
                      />
                    )
                }
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
                  setHelpOpen(
                    true
                  )
                }
                className="
                  inline-flex
                  items-center
                  gap-2
                  rounded-xl
                  border
                  border-slate-200
                  bg-white
                  p-2.5
                  text-slate-600
                  shadow-sm
                  hover:bg-slate-50
                  hover:text-slate-950
                  xl:px-3
                "
                aria-label="Help for this page"
                title="Help for this page"
              >
                <CircleHelp
                  size={18}
                />

                <span
                  className="
                    hidden
                    text-xs
                    font-semibold
                    xl:inline
                  "
                >
                  Help
                </span>
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
              bg-slate-50/70
              px-4
              py-1
              sm:px-6
            "
          >
            <p
              className="
                max-w-5xl
                text-[11px]
                leading-4
                text-slate-500
                sm:text-xs
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
