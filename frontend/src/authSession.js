let accessToken = null;

let sessionCsrfToken = null;

let csrfPromise = null;

let refreshPromise = null;


export function isJwtTokenFailurePayload(
  payload
) {

  return Boolean(
    payload
    && payload.code === "token_not_valid"
  );

}


export function getAccessToken() {

  return accessToken;

}


export function setAccessToken(
  token
) {

  const normalized =
    String(
      token || ""
    ).trim();


  if (!normalized) {

    throw new Error(
      "One UCH access token is unavailable."
    );

  }


  accessToken =
    normalized;


  return accessToken;

}


export function clearAccessToken() {

  accessToken =
    null;

}


export function getSessionCsrfToken() {

  return sessionCsrfToken;

}


export function setSessionCsrfToken(
  token
) {

  const normalized =
    String(
      token || ""
    ).trim();


  if (!normalized) {

    throw new Error(
      "One UCH session verification token is unavailable."
    );

  }


  sessionCsrfToken =
    normalized;


  return sessionCsrfToken;

}


export function clearSessionCsrfToken() {

  sessionCsrfToken =
    null;

}


export function clearBrowserSessionMemory() {

  clearAccessToken();

  clearSessionCsrfToken();

}


/*
 * Phase-F migration cleanup only.
 *
 * F3 never reads access or refresh JWTs from localStorage and
 * never writes JWTs to localStorage. These deletes remove
 * credentials left behind by pre-F3 browser sessions.
 */
export function purgeLegacyStoredAuthTokens(
  storage = window.localStorage
) {

  storage.removeItem(
    "access"
  );

  storage.removeItem(
    "refresh"
  );

}


export async function ensureSessionCsrfToken({
  requestCsrf,
}) {

  if (
    sessionCsrfToken
  ) {

    return sessionCsrfToken;

  }


  if (
    typeof requestCsrf !==
    "function"
  ) {

    throw new Error(
      "Session verification request function is unavailable."
    );

  }


  if (!csrfPromise) {

    csrfPromise =
      Promise.resolve(
        requestCsrf()
      )
        .then(
          (payload) => {

            return (
              setSessionCsrfToken(
                payload?.csrf_token
              )
            );

          }
        )
        .finally(
          () => {

            csrfPromise =
              null;

          }
        );

  }


  return csrfPromise;

}


export async function refreshAccessToken({
  requestRefresh,
}) {

  if (
    typeof requestRefresh !==
    "function"
  ) {

    throw new Error(
      "JWT refresh request function is unavailable."
    );

  }


  /*
   * Preserve the F1 positive control: concurrent API failures
   * share one refresh operation.
   */
  if (!refreshPromise) {

    refreshPromise =
      Promise.resolve(
        requestRefresh()
      )
        .then(
          (payload) => {

            return (
              setAccessToken(
                payload?.access
              )
            );

          }
        )
        .finally(
          () => {

            refreshPromise =
              null;

          }
        );

  }


  return refreshPromise;

}
