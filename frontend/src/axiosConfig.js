import axios from "axios";

import {
  clearBrowserSessionMemory,
  ensureSessionCsrfToken,
  getAccessToken,
  isJwtTokenFailurePayload,
  purgeLegacyStoredAuthTokens,
  refreshAccessToken,
  setAccessToken,
} from "./authSession";

import {
  publishSessionInvalidation,
  withBrowserSessionRotationLock,
} from "./sessionSync";

import {
  API_BASE_URL,
} from "./runtimeConfig";


const instance =
  axios.create({
    baseURL:
      API_BASE_URL,
  });


const sessionClient =
  axios.create({
    baseURL:
      API_BASE_URL,

    withCredentials:
      true,
  });


function csrfHeaders(
  csrfToken
) {

  return {
    "X-OneUCH-CSRF":
      csrfToken,
  };

}


export function invalidateSession(
  reason = "session-invalidated"
) {

  clearBrowserSessionMemory();

  purgeLegacyStoredAuthTokens();

  publishSessionInvalidation(
    reason
  );


  if (
    window.location.pathname !==
    "/login"
  ) {

    window.location.assign(
      "/login"
    );

  }

}


export async function ensureBrowserSessionCsrf() {

  return (
    ensureSessionCsrfToken({

      requestCsrf:
        async () => {

          const response =
            await sessionClient.get(
              "/api/auth/session/csrf/"
            );


          return response.data;

        },

    })
  );

}


export async function establishPasswordBrowserSession({
  email,
  password,
}) {

  const csrfToken =
    await ensureBrowserSessionCsrf();


  const response =
    await sessionClient.post(
      "/api/auth/session/login/",
      {
        email,
        password,
      },
      {
        headers:
          csrfHeaders(
            csrfToken
          ),
      }
    );


  const accessToken =
    setAccessToken(
      response.data?.access
    );


  purgeLegacyStoredAuthTokens();


  return accessToken;

}


export async function exchangeIdentityBrowserSession(
  identityCode
) {

  const csrfToken =
    await ensureBrowserSessionCsrf();


  const response =
    await sessionClient.post(
      (
        "/api/auth/session/"
        + "identity/exchange/"
      ),
      {
        code:
          identityCode,
      },
      {
        headers:
          csrfHeaders(
            csrfToken
          ),
      }
    );


  const accessToken =
    setAccessToken(
      response.data?.access
    );


  purgeLegacyStoredAuthTokens();


  return accessToken;

}


export async function bootstrapBrowserSession() {

  try {

    return await (
      withBrowserSessionRotationLock(
        async () => {

          const csrfToken =
            await ensureBrowserSessionCsrf();


          const response =
            await sessionClient.post(
              "/api/auth/session/bootstrap/",
              {},
              {
                headers:
                  csrfHeaders(
                    csrfToken
                  ),
              }
            );


          if (
            response.data?.authenticated
            !== true
          ) {

            clearBrowserSessionMemory();

            return false;

          }


          setAccessToken(
            response.data?.access
          );

          purgeLegacyStoredAuthTokens();


          return true;

        }
      )
    );

  } catch (error) {

    clearBrowserSessionMemory();


    const status =
      error.response?.status;


    if (
      status === 401
    ) {

      publishSessionInvalidation(
        "bootstrap-rejected"
      );

      return false;

    }


    if (
      status === 404
    ) {

      return false;

    }


    throw error;

  }

}


export async function refreshSessionAccessToken() {

  return (
    refreshAccessToken({

      requestRefresh:
        async () => {

          return (
            withBrowserSessionRotationLock(
              async () => {

                const csrfToken =
                  await ensureBrowserSessionCsrf();


                const response =
                  await sessionClient.post(
                    "/api/auth/session/refresh/",
                    {},
                    {
                      headers:
                        csrfHeaders(
                          csrfToken
                        ),
                    }
                  );


                return response.data;

              }
            )
          );

        },

    })
  );

}


export async function endBrowserSession() {

  const ended =
    await withBrowserSessionRotationLock(
      async () => {

        const csrfToken =
          await ensureBrowserSessionCsrf();


        const response =
          await sessionClient.post(
            "/api/auth/session/end/",
            {},
            {
              headers:
                csrfHeaders(
                  csrfToken
                ),
            }
          );


        return (
          response.data?.ended
          === true
        );

      }
    );


  clearBrowserSessionMemory();

  purgeLegacyStoredAuthTokens();


  if (ended) {

    publishSessionInvalidation(
      "logout"
    );

  }


  return ended;

}


instance.interceptors.request.use(
  (config) => {

    const token =
      getAccessToken();


    if (token) {

      config.headers.Authorization =
        `Bearer ${token}`;

    } else {

      delete config.headers.Authorization;

    }


    return config;

  }
);


instance.interceptors.response.use(

  (response) =>
    response,

  async (error) => {

    const originalRequest =
      error.config;


    const status =
      error.response?.status;


    const payload =
      error.response?.data;


    if (
      status !== 401
      ||
      !originalRequest
      ||
      !isJwtTokenFailurePayload(
        payload
      )
    ) {

      return Promise.reject(
        error
      );

    }


    if (
      originalRequest
        ._oneUchRefreshRetry
    ) {

      invalidateSession(
        "access-refresh-retry-exhausted"
      );

      return Promise.reject(
        error
      );

    }


    originalRequest
      ._oneUchRefreshRetry = true;


    try {

      const accessToken =
        await refreshSessionAccessToken();


      originalRequest.headers =
        originalRequest.headers
        || {};


      originalRequest
        .headers
        .Authorization =
          `Bearer ${accessToken}`;


      return instance(
        originalRequest
      );

    } catch (refreshError) {

      invalidateSession(
        "refresh-rejected"
      );

      return Promise.reject(
        refreshError
      );

    }

  }

);


export default instance;
