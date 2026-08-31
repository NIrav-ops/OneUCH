import {
  WS_BASE_URL,
} from "../runtimeConfig";

import {
  createInboxWebSocket,
} from "../websocketAuth";


let socket = null;

export function getInboxSocket() {

  const token = localStorage.getItem("access");

  if (!socket || socket.readyState === WebSocket.CLOSED) {

    socket = createInboxWebSocket({
      baseUrl:
        WS_BASE_URL,
      accessToken:
        token,
    });

    socket.onopen = () => {
      console.log("WebSocket connected");
    };

    socket.onerror = (err) => {
      console.error("WebSocket error", err);
    };

  }

  return socket;

}