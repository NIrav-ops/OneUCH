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
  API_BASE_URL,
} from "./runtimeConfig";


const instance =
  axios.create({
    baseURL:
      API_BASE_URL,
  });


/*
 * Browser-session transport deliberately has no One UCH
 * response interceptor. Bootstrap/refresh must never recurse
 * back into the access-token refresh lifecycle.
 */
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


export function invalidateSession() {

  clearBrowserSessionMemory();

  purgeLegacyStoredAuthTokens();


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

  } catch (error) {

    clearBrowserSessionMemory();


    const status =
      error.response?.status;


    /*
     * 401 = no valid browser refresh session.
     * 404 = F2/F3 feature remains fail-closed in this runtime.
     */
    if (
      status === 401
      ||
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

        },

    })
  );

}


export async function endBrowserSession() {

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


  clearBrowserSessionMemory();

  purgeLegacyStoredAuthTokens();


  return (
    response.data?.ended
    === true
  );

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


    /*
     * Mailbox provider APIs can legitimately return HTTP 401.
     * Refresh the One UCH browser session only for the exact
     * SimpleJWT token_not_valid contract.
     */
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

      invalidateSession();

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

      invalidateSession();

      return Promise.reject(
        refreshError
      );

    }

  }

);


export default instance;
