import {
  useEffect,
  useState,
} from "react";

import axios from "../axiosConfig";


const EVENT_META = {
  message_received: {
    label:
      "Message received",
    dot:
      "bg-sky-500",
    badge:
      "bg-sky-50 text-sky-700",
  },

  approval_created: {
    label:
      "Approval created",
    dot:
      "bg-amber-500",
    badge:
      "bg-amber-50 text-amber-700",
  },

  approval_approved: {
    label:
      "Approval approved",
    dot:
      "bg-emerald-500",
    badge:
      "bg-emerald-50 text-emerald-700",
  },

  approval_rejected: {
    label:
      "Approval rejected",
    dot:
      "bg-rose-500",
    badge:
      "bg-rose-50 text-rose-700",
  },

  action_created: {
    label:
      "Action created",
    dot:
      "bg-indigo-500",
    badge:
      "bg-indigo-50 text-indigo-700",
  },

  action_completed: {
    label:
      "Action completed",
    dot:
      "bg-emerald-500",
    badge:
      "bg-emerald-50 text-emerald-700",
  },

  followup_created: {
    label:
      "Follow-up created",
    dot:
      "bg-violet-500",
    badge:
      "bg-violet-50 text-violet-700",
  },

  escalated: {
    label:
      "Escalated",
    dot:
      "bg-rose-600",
    badge:
      "bg-rose-50 text-rose-700",
  },
};


function formatDate(
  value
) {

  if (!value) {
    return "Time not recorded";
  }


  try {

    return new Date(
      value
    ).toLocaleString();

  } catch {

    return value;

  }

}


function eventMeta(
  eventType
) {

  if (
    EVENT_META[
      eventType
    ]
  ) {

    return EVENT_META[
      eventType
    ];

  }


  return {
    label:
      String(
        eventType ||
        "Event"
      )
        .replaceAll(
          "_",
          " "
        ),

    dot:
      "bg-slate-400",

    badge:
      "bg-slate-100 text-slate-600",
  };

}


export default function ConversationTimeline({
  conversationId,
}) {

  const [
    events,
    setEvents,
  ] = useState([]);


  const [
    loading,
    setLoading,
  ] = useState(false);


  useEffect(
    () => {

      if (!conversationId) {
        return undefined;
      }


      let cancelled = (
        false
      );


      const loadTimeline =
        async () => {

          try {

            setLoading(
              true
            );


            const response =
              await axios.get(
                `/api/timeline/conversation/${conversationId}/`
              );


            if (!cancelled) {

              setEvents(
                Array.isArray(
                  response.data
                )
                  ? response.data
                  : []
              );

            }

          } catch (error) {

            if (!cancelled) {

              console.error(
                "Timeline load error:",
                error
              );

              setEvents(
                []
              );

            }

          } finally {

            if (!cancelled) {

              setLoading(
                false
              );

            }

          }

        };


      loadTimeline();


      return () => {

        cancelled = (
          true
        );

      };

    },
    [
      conversationId,
    ]
  );


  if (!conversationId) {
    return null;
  }


  return (
    <div className="flex h-full min-h-[320px] flex-col">

      <div className="border-b border-slate-100 px-4 py-4">

        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
          Accountability context
        </p>

        <div className="mt-1 flex items-center justify-between gap-3">

          <h3 className="text-sm font-semibold text-slate-900">
            Conversation timeline
          </h3>

          {!loading && (

            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
              {events.length}
            </span>

          )}

        </div>

        <p className="mt-1.5 text-xs leading-5 text-slate-400">
          Communication and execution events linked to this thread.
        </p>

      </div>


      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">

        {loading ? (

          <div className="py-10 text-center">

            <div className="mx-auto h-7 w-7 animate-pulse rounded-full bg-slate-200" />

            <p className="mt-3 text-xs font-medium text-slate-400">
              Loading timeline...
            </p>

          </div>

        ) : events.length ===
          0 ? (

          <div className="rounded-xl border border-dashed border-slate-200 px-3 py-8 text-center">

            <p className="text-xs font-medium text-slate-600">
              No execution events yet
            </p>

            <p className="mt-1 text-[10px] leading-4 text-slate-400">
              Actions, approvals and follow-ups will appear as the conversation develops.
            </p>

          </div>

        ) : (

          <div className="relative">

            <div className="absolute bottom-3 left-[5px] top-3 w-px bg-slate-200" />


            <div className="space-y-5">

              {events.map(
                (event) => {

                  const meta =
                    eventMeta(
                      event.event_type
                    );


                  return (

                    <div
                      key={
                        event.id
                      }
                      className="relative flex gap-3"
                    >

                      <span
                        className={`relative z-10 mt-1.5 h-[11px] w-[11px] shrink-0 rounded-full ring-4 ring-white ${meta.dot}`}
                      />


                      <div className="min-w-0 flex-1 pb-1">

                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em] ${meta.badge}`}
                        >
                          {meta.label}
                        </span>


                        <p className="mt-2 break-words text-xs font-semibold leading-5 text-slate-800">
                          {event.title ||
                            meta.label}
                        </p>


                        <p className="mt-1 text-[10px] text-slate-400">
                          {formatDate(
                            event.event_at ||
                            event.created_at
                          )}
                        </p>

                      </div>

                    </div>

                  );

                }
              )}

            </div>

          </div>

        )}

      </div>

    </div>
  );

}
