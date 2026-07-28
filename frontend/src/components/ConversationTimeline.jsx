import { useEffect, useState } from "react";
import axios from "../axiosConfig";

export default function ConversationTimeline({
  conversationId,
}) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!conversationId) return;

    loadTimeline();
  }, [conversationId]);

  const loadTimeline = async () => {
    try {
      setLoading(true);

      const res = await axios.get(
        `/api/timeline/conversation/${conversationId}/`
      );

      setEvents(res.data);
    } catch (err) {
      console.error(
        "Timeline load failed",
        err
      );
    } finally {
      setLoading(false);
    }
  };

  const getIcon = (eventType) => {

    switch (eventType) {

      case "message_received":
        return "📧";

      case "approval_created":
        return "🟠";

      case "approval_approved":
        return "✅";

      case "approval_rejected":
        return "❌";

      case "action_created":
        return "📋";

      case "action_completed":
        return "🏁";

      case "followup_created":
        return "⏰";

      case "escalated":
        return "🚨";

      default:
        return "•";
    }
  };

  const getBadgeColor = (eventType) => {

    switch (eventType) {

      case "message_received":
        return "#2563eb";

      case "approval_created":
        return "#f59e0b";

      case "approval_approved":
        return "#16a34a";

      case "approval_rejected":
        return "#dc2626";

      case "action_created":
        return "#059669";

      case "action_completed":
        return "#10b981";

      case "followup_created":
        return "#7c3aed";

      case "escalated":
        return "#ef4444";

      default:
        return "#6b7280";
    }
  };

  if (!conversationId) {
    return null;
  }

  return (
    <div
      style={{
        marginTop: 30,
        borderTop: "1px solid #e5e7eb",
        paddingTop: 20,
      }}
    >
      <h3
        style={{
          marginBottom: 20,
        }}
      >
        Timeline
      </h3>

      {loading && (
        <div>
          Loading timeline...
        </div>
      )}

      {!loading &&
        events.length === 0 && (
          <div>
            No timeline events
          </div>
        )}

      {!loading &&
        events.map((event) => (
          <div
            key={event.id}
            style={{
              display: "flex",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                fontSize: 20,
                width: 28,
              }}
            >
              {getIcon(
                event.event_type
              )}
            </div>

            <div
              style={{
                flex: 1,
              }}
            >
              <div
                style={{
                  display: "inline-block",
                  background:
                    getBadgeColor(
                      event.event_type
                    ),
                  color: "white",
                  borderRadius: 6,
                  padding:
                    "3px 8px",
                  fontSize: 12,
                  marginBottom: 5,
                }}
              >
                {event.event_type
                  .replaceAll(
                    "_",
                    " "
                  )
                  .toUpperCase()}
              </div>

              <div
                style={{
                  fontWeight: 600,
                }}
              >
                {event.title}
              </div>

              <div
                style={{
                  color: "#6b7280",
                  fontSize: 12,
                }}
              >
                {new Date(
                  event.event_at ||
                  event.created_at
                ).toLocaleString()}
              </div>
            </div>
          </div>
        ))}
    </div>
  );
}