let refreshPromise = null;


export function isJwtTokenFailurePayload(
  payload
) {

  return Boolean(
    payload
    && payload.code === "token_not_valid"
  );

}


export function clearStoredAuthTokens(
  storage = window.localStorage
) {

  storage.removeItem(
    "access"
  );

  storage.removeItem(
    "refresh"
  );

}


export async function refreshAccessToken({
  storage = window.localStorage,
  requestRefresh,
}) {

  if (
    typeof requestRefresh !== "function"
  ) {
    throw new Error(
      "JWT refresh request function is unavailable."
    );
  }


  const refreshToken =
    storage.getItem(
      "refresh"
    );


  if (!refreshToken) {
    throw new Error(
      "One UCH refresh token is unavailable."
    );
  }


  /*
   * All requests that discover the same expired access token
   * share one refresh operation. This prevents a burst of API
   * 401s from issuing multiple competing refresh requests.
   */
  if (!refreshPromise) {

    refreshPromise = Promise.resolve(
      requestRefresh(
        refreshToken
      )
    )
      .then((payload) => {

        const accessToken =
          payload?.access;


        if (!accessToken) {
          throw new Error(
            "JWT refresh response did not contain an access token."
          );
        }


        storage.setItem(
          "access",
          accessToken
        );


        /*
         * SimpleJWT does not rotate refresh tokens by default,
         * but preserve a rotated token if deployment policy
         * enables rotation later.
         */
        if (payload?.refresh) {

          storage.setItem(
            "refresh",
            payload.refresh
          );

        }


        return accessToken;

      })
      .finally(() => {

        refreshPromise = null;

      });

  }


  return refreshPromise;

}
