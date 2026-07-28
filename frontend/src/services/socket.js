let socket = null;

export function getInboxSocket() {

  const token = localStorage.getItem("access");

  if (!socket || socket.readyState === WebSocket.CLOSED) {

    socket = new WebSocket(
      `ws://127.0.0.1:8000/ws/inbox/?token=${token}`
    );

    socket.onopen = () => {
      console.log("WebSocket connected");
    };

    socket.onerror = (err) => {
      console.error("WebSocket error", err);
    };

  }

  return socket;

}