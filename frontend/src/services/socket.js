import {
  WS_BASE_URL,
} from "../runtimeConfig";

import {
  getAccessToken,
} from "../authSession";

import {
  createInboxWebSocket,
} from "../websocketAuth";


let socket = null;


export function getInboxSocket() {

  const token =
    getAccessToken();


  if (
    !socket
    ||
    socket.readyState ===
      WebSocket.CLOSED
  ) {

    socket = createInboxWebSocket({
      baseUrl:
        WS_BASE_URL,

      accessToken:
        token,
    });


    socket.onopen = () => {

      console.log(
        "WebSocket connected"
      );

    };


    socket.onerror = (err) => {

      console.error(
        "WebSocket error",
        err
      );

    };

  }


  return socket;

}
