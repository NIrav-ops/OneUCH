import {
  useEffect,
  useState,
} from "react";

import axios from "../axiosConfig";


function formatDate(
  value
) {

  if (!value) {
    return "Time unavailable";
  }


  const parsed =
    new Date(
      value
    );


  if (
    Number.isNaN(
      parsed.getTime()
    )
  ) {
    return String(
      value
    );
  }


  return parsed.toLocaleString();

}


export default function Notifications() {

  const [
    notifications,
    setNotifications,
  ] = useState([]);


  const [
    unreadCount,
    setUnreadCount,
  ] = useState(0);


  const [
    error,
    setError,
  ] = useState("");


  const loadNotifications =
    async () => {

      try {

        setError(
          ""
        );


        const res =
          await axios.get(
            "/api/notifications/"
          );


        setNotifications(
          res.data?.notifications ||
          []
        );


        setUnreadCount(
          res.data?.unread_count ||
          0
        );

      } catch (err) {

        console.error(
          "Notification load error:",
          err
        );


        setError(
          "Unable to load notifications."
        );

      }

    };


  useEffect(
    () => {

      let cancelled =
        false;


      const fetchNotifications =
        async () => {

          try {

            const res =
              await axios.get(
                "/api/notifications/"
              );


            if (cancelled) {
              return;
            }


            setNotifications(
              res.data?.notifications ||
              []
            );


            setUnreadCount(
              res.data?.unread_count ||
              0
            );

          } catch (err) {

            if (!cancelled) {

              console.error(
                "Notification load error:",
                err
              );


              setError(
                "Unable to load notifications."
              );

            }

          }

        };


      fetchNotifications();


      return () => {

        cancelled =
          true;

      };

    },
    []
  );


  const markRead =
    async (
      id
    ) => {

      try {

        await axios.post(
          `/api/notifications/${id}/read/`
        );


        await loadNotifications();

      } catch (err) {

        console.error(
          "Mark notification read error:",
          err
        );


        setError(
          "Unable to mark this notification as read."
        );

      }

    };


  const markAllRead =
    async () => {

      try {

        await axios.post(
          "/api/notifications/read-all/"
        );


        await loadNotifications();

      } catch (err) {

        console.error(
          "Mark all notifications read error:",
          err
        );


        setError(
          "Unable to mark all notifications as read."
        );

      }

    };


  const readCount =
    Math.max(
      0,
      notifications.length -
      unreadCount
    );


  return (
    <div className="min-h-full bg-slate-50/70 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">

      <div className="mx-auto max-w-[1540px]">


        <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 text-white shadow-sm">

          <div className="absolute right-0 top-0 h-56 w-56 rounded-full bg-sky-500/10 blur-3xl" />

          <div className="relative flex flex-col gap-6 px-6 py-7 lg:flex-row lg:items-end lg:justify-between lg:px-8 lg:py-8">

            <div className="max-w-3xl">

              <div className="inline-flex rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.17em] text-slate-300">
                Workspace activity
              </div>

              <h1 className="mt-5 text-3xl font-semibold tracking-tight lg:text-4xl">
                Notifications
              </h1>

              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300 lg:text-base">
                Review workspace events and clear items that no longer need your attention.
              </p>

            </div>


            <button
              type="button"
              onClick={
                markAllRead
              }
              disabled={
                unreadCount ===
                0
              }
              className="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Mark all read
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
              Total
            </p>

            <p className="mt-3 text-3xl font-semibold text-slate-950">
              {notifications.length}
            </p>

          </div>


          <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Unread
            </p>

            <p className="mt-3 text-3xl font-semibold text-rose-700">
              {unreadCount}
            </p>

          </div>


          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm">

            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Reviewed
            </p>

            <p className="mt-3 text-3xl font-semibold text-emerald-800">
              {readCount}
            </p>

          </div>

        </section>


        <section className="mt-5 overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">

          <div className="border-b border-slate-100 px-5 py-4 sm:px-6">

            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-sky-500">
              Activity stream
            </p>

            <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
              Workspace notifications
            </h2>

          </div>


          {notifications.length ===
          0 ? (

            <div className="px-6 py-16 text-center">

              <p className="text-sm font-semibold text-slate-700">
                No notifications
              </p>

              <p className="mt-1 text-xs text-slate-400">
                New workspace events will appear here.
              </p>

            </div>

          ) : (

            <div className="divide-y divide-slate-100">

              {notifications.map(
                (item) => (

                  <article
                    key={
                      item.id
                    }
                    className={`px-5 py-4 sm:px-6 ${
                      item.is_read
                        ? "bg-white"
                        : "bg-sky-50/50"
                    }`}
                  >

                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

                      <div className="min-w-0">

                        <div className="flex items-center gap-2">

                          {!item.is_read && (

                            <span className="h-2 w-2 shrink-0 rounded-full bg-sky-500" />

                          )}

                          <h3 className="text-sm font-semibold text-slate-900">
                            {item.title ||
                              "Workspace notification"}
                          </h3>

                        </div>


                        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
                          {item.message}
                        </p>


                        <p className="mt-2 text-[10px] font-medium text-slate-400">
                          {formatDate(
                            item.created_at
                          )}
                        </p>

                      </div>


                      {!item.is_read && (

                        <button
                          type="button"
                          onClick={() =>
                            markRead(
                              item.id
                            )
                          }
                          className="shrink-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                        >
                          Mark read
                        </button>

                      )}

                    </div>

                  </article>

                )
              )}

            </div>

          )}

        </section>

      </div>

    </div>
  );

}
