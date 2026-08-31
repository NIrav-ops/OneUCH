const LOCAL_DEVELOPMENT_API_URL =
  "http://127.0.0.1:8000";


function normalizeBaseUrl(value) {

  return String(
    value || ""
  )
    .trim()
    .replace(
      /\/+$/,
      ""
    );

}


function resolveApiBaseUrl() {

  const configured =
    normalizeBaseUrl(
      import.meta.env.VITE_API_BASE_URL
    );


  if (configured) {
    return configured;
  }


  /*
   * Preserve the existing local Vite + Django workflow.
   *
   * In a production build we deliberately do NOT fall back
   * to localhost because localhost would refer to the pilot
   * user's machine rather than the One UCH backend.
   */
  if (import.meta.env.DEV) {
    return LOCAL_DEVELOPMENT_API_URL;
  }


  if (
    typeof window !== "undefined"
    && window.location?.origin
  ) {
    return normalizeBaseUrl(
      window.location.origin
    );
  }


  throw new Error(
    "Unable to resolve One UCH API base URL."
  );

}


function apiUrlToWebSocketUrl(
  apiBaseUrl
) {

  if (
    apiBaseUrl.startsWith(
      "https://"
    )
  ) {
    return (
      "wss://"
      + apiBaseUrl.slice(8)
    );
  }


  if (
    apiBaseUrl.startsWith(
      "http://"
    )
  ) {
    return (
      "ws://"
      + apiBaseUrl.slice(7)
    );
  }


  throw new Error(
    "One UCH API base URL must use HTTP or HTTPS."
  );

}


export const API_BASE_URL =
  resolveApiBaseUrl();


const configuredWebSocketUrl =
  normalizeBaseUrl(
    import.meta.env.VITE_WS_BASE_URL
  );


export const WS_BASE_URL =
  configuredWebSocketUrl
  || apiUrlToWebSocketUrl(
    API_BASE_URL
  );
