import axios from "axios";

import {
  clearStoredAuthTokens,
  isJwtTokenFailurePayload,
  refreshAccessToken,
} from "./authSession";

import {
  API_BASE_URL,
} from "./runtimeConfig";


const instance = axios.create({
  baseURL: API_BASE_URL,
});


/*
 * Dedicated client deliberately has no One UCH response
 * interceptor. The refresh request itself must never recurse
 * back into the refresh lifecycle.
 */
const refreshClient = axios.create({
  baseURL: API_BASE_URL,
});


export function invalidateSession() {

  clearStoredAuthTokens();


  if (
    window.location.pathname !==
    "/login"
  ) {

    window.location.assign(
      "/login"
    );

  }

}


export async function refreshSessionAccessToken() {

  return refreshAccessToken({

    requestRefresh:
      async (refreshToken) => {

        const response =
          await refreshClient.post(
            "/api/auth/token/refresh/",
            {
              refresh:
                refreshToken,
            }
          );


        return response.data;

      },

  });

}


instance.interceptors.request.use(
  (config) => {

    const token =
      localStorage.getItem(
        "access"
      );


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
     * IMPORTANT:
     *
     * One UCH provider endpoints can legitimately use HTTP 401
     * to mean mailbox/provider re-authentication is required.
     *
     * Only SimpleJWT's token_not_valid contract means the
     * One UCH access token itself needs refreshing.
     */
    if (
      status !== 401
      || !originalRequest
      || !isJwtTokenFailurePayload(
        payload
      )
    ) {

      return Promise.reject(
        error
      );

    }


    /*
     * The replayed request is allowed exactly one JWT refresh
     * cycle. A second JWT authentication failure means the
     * refreshed session cannot be trusted.
     */
    if (
      originalRequest
        ._oneUchRefreshRetry
    ) {

      invalidateSession();

      return Promise.reject(
        error
      );

    }


    if (
      !localStorage.getItem(
        "refresh"
      )
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
        originalRequest.headers || {};


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
