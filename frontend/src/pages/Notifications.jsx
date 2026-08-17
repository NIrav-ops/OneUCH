import { useEffect, useState } from "react";
import axios from "../axiosConfig";

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const loadNotifications = async () => {
    try {
      const res = await axios.get(
        "/api/notifications/"
      );

      setNotifications(
        res.data?.notifications || []
      );

      setUnreadCount(
        res.data?.unread_count || 0
      );
    } catch (err) {
      console.error(
        "Notification load error:",
        err
      );
    }
  };

  useEffect(() => {
    let cancelled = false;

    const fetchNotifications = async () => {
      try {
        const res = await axios.get(
          "/api/notifications/"
        );

        if (cancelled) {
          return;
        }

        setNotifications(
          res.data?.notifications || []
        );

        setUnreadCount(
          res.data?.unread_count || 0
        );
      } catch (err) {
        if (!cancelled) {
          console.error(
            "Notification load error:",
            err
          );
        }
      }
    };

    fetchNotifications();

    return () => {
      cancelled = true;
    };
  }, []);

  const markRead = async (id) => {
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
    }
  };

  const markAllRead = async () => {
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
    }
  };

  return (
    <div className="p-6">

      <div className="flex justify-between mb-4">

        <div>
          <h1 className="text-2xl font-bold">
            Notifications
          </h1>

          <p className="text-gray-500">
            Unread: {unreadCount}
          </p>
        </div>

        <button
          onClick={markAllRead}
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          Mark All Read
        </button>

      </div>

      <div className="space-y-3">

        {notifications.map((item) => (
          <div
            key={item.id}
            className={`border rounded p-4 ${
              item.is_read
                ? "bg-white"
                : "bg-blue-50"
            }`}
          >

            <div className="flex justify-between">

              <div>

                <h3 className="font-semibold">
                  {item.title}
                </h3>

                <p className="text-gray-600">
                  {item.message}
                </p>

                <p className="text-xs text-gray-400">
                  {item.created_at}
                </p>

              </div>

              {!item.is_read && (
                <button
                  onClick={() =>
                    markRead(item.id)
                  }
                  className="bg-green-600 text-white px-3 py-1 rounded"
                >
                  Read
                </button>
              )}

            </div>

          </div>
        ))}

      </div>

    </div>
  );
}