export const WS_AUTH_SUBPROTOCOL =
  "oneuch.jwt";


export function createInboxWebSocket({
  baseUrl,
  accessToken,
  WebSocketImpl = WebSocket,
}) {

  if (!accessToken) {
    throw new Error(
      "One UCH access token is required for WebSocket authentication."
    );
  }


  if (!baseUrl) {
    throw new Error(
      "One UCH WebSocket base URL is required."
    );
  }


  /*
   * Keep bearer credentials out of the WebSocket URL.
   *
   * Browser WebSocket APIs cannot set an Authorization header,
   * so the existing access JWT is carried as a requested
   * subprotocol alongside a fixed marker.
   *
   * The server negotiates only WS_AUTH_SUBPROTOCOL and never
   * echoes the JWT as the selected protocol.
   */
  return new WebSocketImpl(
    `${baseUrl}/ws/inbox/`,
    [
      WS_AUTH_SUBPROTOCOL,
      accessToken,
    ]
  );

}
