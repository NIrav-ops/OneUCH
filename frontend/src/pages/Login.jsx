
import {
  useEffect,
  useState,
} from "react";

import {
  ArrowRight,
  Check,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";

import axios, {
  establishPasswordBrowserSession,
  exchangeIdentityBrowserSession,
} from "../axiosConfig";

import {
  API_BASE_URL,
} from "../runtimeConfig";


const VALUE_POINTS = [
  "Unified communication across all connected work mailboxes",
  "Actions, approvals and commitments from real conversations",
  "Attention, accountability and execution in one workspace",
];


const IDENTITY_PROVIDER_LABELS = {
  google: "Google",
  microsoft: "Microsoft",
};


const AUTH_CALLBACK_QUERY_KEYS = [
  "identity_code",
  "identity_provider",
  "identity_error",
  "registration_status",
  "registration_id",
  "registration_created",
  "registration_error",
];


function cleanAuthCallbackUrl() {

  const url =
    new URL(
      window.location.href
    );


  AUTH_CALLBACK_QUERY_KEYS.forEach(
    (key) => {

      url.searchParams.delete(
        key
      );

    }
  );


  window.history.replaceState(
    {},
    document.title,
    (
      url.pathname
      + url.search
      + url.hash
    )
  );

}


function buildIdentityStartUrl(
  provider
) {

  if (
    !IDENTITY_PROVIDER_LABELS[
      provider
    ]
  ) {

    throw new Error(
      "Unsupported identity provider."
    );

  }


  const api =
    new URL(
      API_BASE_URL
    );


  if (
    api.protocol !== "http:"
    &&
    api.protocol !== "https:"
  ) {

    throw new Error(
      "Invalid One UCH API URL."
    );

  }


  return new URL(
    (
      "/api/auth/identity/"
      + provider
      + "/start/"
    ),
    api.origin
  ).toString();

}


function safeRegistrationStatus(
  value
) {

  return [
    "pending",
    "approved",
    "rejected",
  ].includes(
    value
  )
    ? value
    : "";

}


export default function Login({
  onLogin,
}) {

  const [
    email,
    setEmail,
  ] = useState("");


  const [
    password,
    setPassword,
  ] = useState("");


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  const [
    identityProviders,
    setIdentityProviders,
  ] = useState([]);


  const [
    identityAction,
    setIdentityAction,
  ] = useState("");


  const [
    authMode,
    setAuthMode,
  ] = useState(
    "signin"
  );


  const [
    registrationConfig,
    setRegistrationConfig,
  ] = useState({
    enabled: false,
    providers: [],
    privacy_notice_version: "",
    terms_version: "",
  });


  const [
    organizationName,
    setOrganizationName,
  ] = useState("");


  const [
    registrationAcknowledged,
    setRegistrationAcknowledged,
  ] = useState(false);


  const [
    registrationAction,
    setRegistrationAction,
  ] = useState("");


  const [
    registrationOutcome,
    setRegistrationOutcome,
  ] = useState(null);


  useEffect(
    () => {

      let active = true;


      const initializeAuth =
        async () => {

          const currentUrl =
            new URL(
              window.location.href
            );


          const identityCode =
            currentUrl.searchParams.get(
              "identity_code"
            );


          const identityProvider =
            currentUrl.searchParams.get(
              "identity_provider"
            );


          const identityError =
            currentUrl.searchParams.get(
              "identity_error"
            );


          const registrationStatus =
            safeRegistrationStatus(
              currentUrl.searchParams.get(
                "registration_status"
              )
            );


          const registrationId =
            currentUrl.searchParams.get(
              "registration_id"
            );


          const registrationError =
            currentUrl.searchParams.get(
              "registration_error"
            );


          const hasCallbackState =
            AUTH_CALLBACK_QUERY_KEYS.some(
              (key) =>
                currentUrl.searchParams.has(
                  key
                )
            );


          if (hasCallbackState) {

            cleanAuthCallbackUrl();

          }


          if (
            registrationError
            &&
            active
          ) {

            setRegistrationOutcome({
              status: "error",
              registrationId: "",
              provider:
                identityProvider || "",
            });

            setAuthMode(
              "request"
            );

          } else if (
            registrationStatus
            &&
            active
          ) {

            setRegistrationOutcome({
              status:
                registrationStatus,

              registrationId:
                registrationId || "",

              provider:
                identityProvider || "",
            });


            setAuthMode(
              registrationStatus ===
                "approved"
                ? "signin"
                : "request"
            );

          }


          if (
            identityError
            &&
            active
          ) {

            setError(
              identityError ===
                "provider_unavailable"
                ? (
                    "This identity provider is not available right now."
                  )
                : (
                    "We couldn't complete identity sign-in. Try again."
                  )
            );

          }


          if (identityCode) {

            try {

              if (active) {

                setLoading(
                  true
                );

                setError(
                  ""
                );

              }


              await exchangeIdentityBrowserSession(
                identityCode
              );


              if (active) {

                onLogin();

                return;

              }


            } catch {

              if (active) {

                setError(
                  "We couldn't complete identity sign-in. Try again."
                );

              }


            } finally {

              if (active) {

                setLoading(
                  false
                );

              }

            }

          }


          try {

            const response =
              await axios.get(
                "/api/auth/identity/providers/"
              );


            const providers =
              Array.isArray(
                response.data?.providers
              )
                ? (
                    response.data.providers
                      .filter(
                        (provider) =>
                          Boolean(
                            IDENTITY_PROVIDER_LABELS[
                              provider
                            ]
                          )
                      )
                  )
                : [];


            if (active) {

              setIdentityProviders(
                providers
              );

            }


          } catch {

            if (active) {

              setIdentityProviders(
                []
              );

            }

          }


          try {

            const response =
              await axios.get(
                (
                  "/api/auth/identity/"
                  + "registration/config/"
                )
              );


            const providers =
              Array.isArray(
                response.data?.providers
              )
                ? (
                    response.data.providers
                      .filter(
                        (provider) =>
                          Boolean(
                            IDENTITY_PROVIDER_LABELS[
                              provider
                            ]
                          )
                      )
                  )
                : [];


            if (active) {

              setRegistrationConfig({
                enabled:
                  response.data?.enabled ===
                  true,

                providers,

                privacy_notice_version:
                  String(
                    response.data
                      ?.privacy_notice_version
                    || ""
                  ),

                terms_version:
                  String(
                    response.data
                      ?.terms_version
                    || ""
                  ),
              });

            }


          } catch {

            if (active) {

              setRegistrationConfig({
                enabled: false,
                providers: [],
                privacy_notice_version: "",
                terms_version: "",
              });

            }

          }

        };


      const timer =
        window.setTimeout(
          () => {

            void initializeAuth();

          },
          0
        );


      return () => {

        active = false;

        window.clearTimeout(
          timer
        );

      };

    },
    [
      onLogin,
    ]
  );


  const registrationProviders =
    registrationConfig.providers.filter(
      (provider) =>
        IDENTITY_PROVIDER_LABELS[
          provider
        ]
    );


  const handleIdentityStart =
    (provider) => {

      if (
        !identityProviders.includes(
          provider
        )
        ||
        identityAction
        ||
        registrationAction
        ||
        loading
      ) {

        return;

      }


      try {

        setIdentityAction(
          provider
        );

        setError(
          ""
        );


        window.location.assign(
          buildIdentityStartUrl(
            provider
          )
        );


      } catch {

        setIdentityAction(
          ""
        );

        setError(
          "We couldn't start identity sign-in. Try again."
        );

      }

    };


  const handleRegistrationStart =
    async (provider) => {

      if (
        !registrationConfig.enabled
        ||
        !registrationProviders.includes(
          provider
        )
        ||
        registrationAction
        ||
        identityAction
        ||
        loading
      ) {

        return;

      }


      if (!organizationName.trim()) {

        setError(
          "Enter your company or workspace name."
        );

        return;

      }


      if (!registrationAcknowledged) {

        setError(
          "Acknowledge the Privacy Notice and Terms before requesting access."
        );

        return;

      }


      try {

        setRegistrationAction(
          provider
        );

        setError(
          ""
        );


        const response =
          await axios.post(
            (
              "/api/auth/identity/"
              + "registration/"
              + provider
              + "/start/"
            ),
            {
              organization_name:
                organizationName.trim(),

              acknowledged:
                true,
            },
            {
              withCredentials:
                true,
            }
          );


        const authorizationUrl =
          String(
            response.data
              ?.authorization_url
            || ""
          ).trim();


        if (!authorizationUrl) {

          throw new Error(
            "Missing authorization URL."
          );

        }


        const target =
          new URL(
            authorizationUrl
          );


        if (
          target.protocol !== "https:"
          &&
          target.protocol !== "http:"
        ) {

          throw new Error(
            "Invalid authorization URL."
          );

        }


        window.location.assign(
          target.toString()
        );


      } catch {

        setRegistrationAction(
          ""
        );

        setError(
          "We couldn't start the access request. Try again."
        );

      }

    };


  const handleLogin =
    async (event) => {

      event.preventDefault();


      if (
        !email.trim()
        ||
        !password
      ) {

        setError(
          "Enter your email and password."
        );

        return;

      }


      try {

        setLoading(
          true
        );

        setError(
          ""
        );


        await establishPasswordBrowserSession({
          email:
            email.trim(),

          password,
        });


        onLogin();


      } catch (loginError) {

        console.error(
          "Login failed:",
          loginError
        );


        setError(
          "We couldn't sign you in. Check your credentials and try again."
        );


      } finally {

        setLoading(
          false
        );

      }

    };


  const switchMode =
    (mode) => {

      setAuthMode(
        mode
      );

      setError(
        ""
      );

      setRegistrationOutcome(
        null
      );

    };


  const outcomeStatus =
    registrationOutcome?.status
    || "";


  const outcomeProviderLabel =
    IDENTITY_PROVIDER_LABELS[
      registrationOutcome?.provider
    ]
    || "your work identity";


  const registrationBlocked =
    [
      "pending",
      "rejected",
      "error",
    ].includes(
      outcomeStatus
    );


  return (
    <div
      className="
        min-h-screen
        bg-slate-950
        text-slate-950
        lg:grid
        lg:grid-cols-[1.05fr_0.95fr]
      "
    >

      <section
        className="
          relative
          hidden
          min-h-screen
          overflow-hidden
          border-r
          border-white/10
          bg-slate-950
          px-12
          py-12
          text-white
          lg:flex
          lg:flex-col
          lg:justify-between
        "
      >
        <div
          className="
            pointer-events-none
            absolute
            -right-40
            -top-40
            h-96
            w-96
            rounded-full
            bg-indigo-500/10
            blur-3xl
          "
        />

        <div
          className="
            pointer-events-none
            absolute
            -bottom-48
            -left-36
            h-[28rem]
            w-[28rem]
            rounded-full
            bg-cyan-400/10
            blur-3xl
          "
        />


        <div
          className="
            relative
            z-10
            flex
            items-center
            gap-3
          "
        >
          <div
            className="
              flex
              h-11
              w-11
              items-center
              justify-center
              rounded-xl
              bg-white
              text-sm
              font-black
              text-slate-950
            "
          >
            OU
          </div>

          <div>
            <div
              className="
                text-base
                font-semibold
                tracking-tight
              "
            >
              One UCH
            </div>

            <div
              className="
                text-[10px]
                font-semibold
                uppercase
                tracking-[0.2em]
                text-slate-400
              "
            >
              Communication Intelligence
            </div>
          </div>
        </div>


        <div
          className="
            relative
            z-10
            max-w-xl
          "
        >
          <div
            className="
              mb-5
              inline-flex
              items-center
              gap-2
              rounded-full
              border
              border-white/10
              bg-white/5
              px-3
              py-1.5
              text-xs
              font-medium
              text-slate-300
            "
          >
            <ShieldCheck
              size={15}
            />

            Governed enterprise workspace
          </div>


          <h1
            className="
              text-4xl
              font-semibold
              leading-[1.12]
              tracking-[-0.035em]
              xl:text-5xl
            "
          >
            Turn communication into accountable execution.
          </h1>


          <p
            className="
              mt-5
              max-w-lg
              text-base
              leading-7
              text-slate-400
            "
          >
            One UCH connects communication, intelligence,
            action and accountability without forcing teams
            into another chat application.
          </p>


          <div
            className="
              mt-8
              space-y-3
            "
          >
            {
              VALUE_POINTS.map(
                (point) => (

                  <div
                    key={point}
                    className="
                      flex
                      items-start
                      gap-3
                      text-sm
                      text-slate-300
                    "
                  >
                    <span
                      className="
                        mt-0.5
                        flex
                        h-5
                        w-5
                        shrink-0
                        items-center
                        justify-center
                        rounded-full
                        bg-white/10
                        text-white
                      "
                    >
                      <Check
                        size={12}
                      />
                    </span>

                    <span>
                      {point}
                    </span>
                  </div>

                )
              )
            }
          </div>
        </div>


        <div
          className="
            relative
            z-10
            text-xs
            text-slate-500
          "
        >
          Communication &rarr; Intelligence &rarr; Action &rarr; Accountability &rarr; Execution
        </div>
      </section>


      <section
        className="
          flex
          min-h-screen
          items-center
          justify-center
          bg-slate-50
          px-5
          py-8
          sm:px-8
        "
      >
        <div
          className="
            w-full
            max-w-md
          "
        >

          <div
            className="
              mb-6
              flex
              items-center
              gap-3
              lg:hidden
            "
          >
            <div
              className="
                flex
                h-10
                w-10
                items-center
                justify-center
                rounded-xl
                bg-slate-950
                text-xs
                font-black
                text-white
              "
            >
              OU
            </div>

            <div>
              <div
                className="
                  text-sm
                  font-semibold
                  text-slate-950
                "
              >
                One UCH
              </div>

              <div
                className="
                  text-[10px]
                  font-semibold
                  uppercase
                  tracking-[0.16em]
                  text-slate-400
                "
              >
                Communication Intelligence
              </div>
            </div>
          </div>


          <div
            className="
              rounded-2xl
              border
              border-slate-200
              bg-white
              p-6
              shadow-xl
              shadow-slate-200/40
              sm:p-7
            "
          >

            {
              registrationConfig.enabled
              &&
              registrationProviders.length > 0
              && (

                <div
                  className="
                    mb-6
                    grid
                    grid-cols-2
                    rounded-xl
                    bg-slate-100
                    p-1
                  "
                  role="tablist"
                  aria-label="Workspace access"
                >
                  <button
                    type="button"
                    role="tab"
                    aria-selected={
                      authMode ===
                      "signin"
                    }
                    onClick={() =>
                      switchMode(
                        "signin"
                      )
                    }
                    className={`
                      rounded-lg
                      px-3
                      py-2
                      text-xs
                      font-semibold
                      transition
                      ${
                        authMode ===
                        "signin"
                          ? (
                              "bg-white text-slate-950 shadow-sm"
                            )
                          : (
                              "text-slate-500 hover:text-slate-800"
                            )
                      }
                    `}
                  >
                    Sign in
                  </button>

                  <button
                    type="button"
                    role="tab"
                    aria-selected={
                      authMode ===
                      "request"
                    }
                    onClick={() =>
                      switchMode(
                        "request"
                      )
                    }
                    className={`
                      rounded-lg
                      px-3
                      py-2
                      text-xs
                      font-semibold
                      transition
                      ${
                        authMode ===
                        "request"
                          ? (
                              "bg-white text-slate-950 shadow-sm"
                            )
                          : (
                              "text-slate-500 hover:text-slate-800"
                            )
                      }
                    `}
                  >
                    Request access
                  </button>
                </div>

              )
            }


            <div
              className="
                mb-6
              "
            >
              <div
                className="
                  mb-4
                  flex
                  h-10
                  w-10
                  items-center
                  justify-center
                  rounded-xl
                  bg-slate-100
                  text-slate-700
                "
              >
                {
                  authMode ===
                    "request"
                    ? (
                        <ShieldCheck
                          size={19}
                        />
                      )
                    : (
                        <LockKeyhole
                          size={19}
                        />
                      )
                }
              </div>


              <h2
                className="
                  text-2xl
                  font-semibold
                  tracking-tight
                  text-slate-950
                "
              >
                {
                  authMode ===
                    "request"
                    ? "Request workspace access"
                    : "Welcome back"
                }
              </h2>


              <p
                className="
                  mt-2
                  text-sm
                  leading-6
                  text-slate-500
                "
              >
                {
                  authMode ===
                    "request"
                    ? (
                        "Verify your work identity and submit your organization for One UCH approval."
                      )
                    : (
                        "Sign in to your approved One UCH workspace."
                      )
                }
              </p>
            </div>


            {
              registrationOutcome
              && (

                <div
                  className={`
                    mb-5
                    rounded-xl
                    border
                    px-4
                    py-3
                    text-sm
                    ${
                      outcomeStatus ===
                        "approved"
                        ? (
                            "border-emerald-200 bg-emerald-50 text-emerald-800"
                          )
                        : outcomeStatus ===
                            "pending"
                          ? (
                              "border-amber-200 bg-amber-50 text-amber-800"
                            )
                          : (
                              "border-rose-200 bg-rose-50 text-rose-800"
                            )
                    }
                  `}
                  role="status"
                >
                  <div
                    className="
                      font-semibold
                    "
                  >
                    {
                      outcomeStatus ===
                        "approved"
                        ? "Access approved"
                        : outcomeStatus ===
                            "pending"
                          ? "Access request pending"
                          : outcomeStatus ===
                              "rejected"
                            ? "Access request not approved"
                            : "Access request could not be completed"
                    }
                  </div>

                  <div
                    className="
                      mt-1
                      text-xs
                      leading-5
                      opacity-90
                    "
                  >
                    {
                      outcomeStatus ===
                        "approved"
                        ? (
                            `Your workspace is approved. Sign in with ${outcomeProviderLabel}.`
                          )
                        : outcomeStatus ===
                            "pending"
                          ? (
                              "Your identity is verified, but workspace access remains disabled until One UCH platform approval."
                            )
                          : outcomeStatus ===
                              "rejected"
                            ? (
                                "This registration remains disabled. Contact One UCH platform administration if the request requires review."
                              )
                            : (
                                "No workspace was activated. Please try the request again."
                              )
                    }
                  </div>

                  {
                    registrationOutcome
                      .registrationId
                    && (

                      <div
                        className="
                          mt-2
                          font-mono
                          text-[10px]
                          font-semibold
                          uppercase
                          tracking-[0.08em]
                          opacity-70
                        "
                      >
                        {
                          registrationOutcome
                            .registrationId
                        }
                      </div>

                    )
                  }
                </div>

              )
            }


            {
              error
              && (

                <div
                  role="alert"
                  className="
                    mb-5
                    rounded-xl
                    border
                    border-rose-200
                    bg-rose-50
                    px-3
                    py-2.5
                    text-xs
                    leading-5
                    text-rose-700
                  "
                >
                  {error}
                </div>

              )
            }


            {
              authMode ===
                "signin"
                ? (

                    <>
                      <form
                        onSubmit={
                          handleLogin
                        }
                        className="
                          space-y-4
                        "
                      >
                        <div>
                          <label
                            htmlFor="oneuch-email"
                            className="
                              mb-1.5
                              block
                              text-xs
                              font-semibold
                              text-slate-700
                            "
                          >
                            Email address
                          </label>

                          <div
                            className="
                              flex
                              items-center
                              gap-2.5
                              rounded-xl
                              border
                              border-slate-200
                              bg-white
                              px-3
                              focus-within:border-slate-400
                              focus-within:ring-2
                              focus-within:ring-slate-100
                            "
                          >
                            <Mail
                              size={16}
                              className="
                                shrink-0
                                text-slate-400
                              "
                            />

                            <input
                              id="oneuch-email"
                              type="email"
                              autoComplete="email"
                              value={email}
                              onChange={
                                (event) =>
                                  setEmail(
                                    event.target.value
                                  )
                              }
                              placeholder="name@company.com"
                              className="
                                w-full
                                bg-transparent
                                py-3
                                text-sm
                                text-slate-900
                                outline-none
                                placeholder:text-slate-400
                              "
                            />
                          </div>
                        </div>


                        <div>
                          <label
                            htmlFor="oneuch-password"
                            className="
                              mb-1.5
                              block
                              text-xs
                              font-semibold
                              text-slate-700
                            "
                          >
                            Password
                          </label>

                          <div
                            className="
                              flex
                              items-center
                              gap-2.5
                              rounded-xl
                              border
                              border-slate-200
                              bg-white
                              px-3
                              focus-within:border-slate-400
                              focus-within:ring-2
                              focus-within:ring-slate-100
                            "
                          >
                            <LockKeyhole
                              size={16}
                              className="
                                shrink-0
                                text-slate-400
                              "
                            />

                            <input
                              id="oneuch-password"
                              type="password"
                              autoComplete="current-password"
                              value={password}
                              onChange={
                                (event) =>
                                  setPassword(
                                    event.target.value
                                  )
                              }
                              placeholder="Enter your password"
                              className="
                                w-full
                                bg-transparent
                                py-3
                                text-sm
                                text-slate-900
                                outline-none
                                placeholder:text-slate-400
                              "
                            />
                          </div>
                        </div>


                        <button
                          type="submit"
                          disabled={
                            loading
                            ||
                            Boolean(
                              identityAction
                            )
                            ||
                            Boolean(
                              registrationAction
                            )
                          }
                          className="
                            flex
                            w-full
                            items-center
                            justify-center
                            gap-2
                            rounded-xl
                            bg-slate-950
                            px-4
                            py-3
                            text-sm
                            font-semibold
                            text-white
                            shadow-sm
                            transition
                            hover:bg-slate-800
                            disabled:cursor-not-allowed
                            disabled:opacity-60
                          "
                        >
                          {
                            loading
                              ? "Signing in..."
                              : "Sign in securely"
                          }

                          {
                            !loading
                            && (
                              <ArrowRight
                                size={16}
                              />
                            )
                          }
                        </button>
                      </form>


                      {
                        identityProviders.length > 0
                        && (

                          <div
                            className="
                              mt-6
                            "
                          >
                            <div
                              className="
                                flex
                                items-center
                                gap-3
                                text-[10px]
                                font-semibold
                                uppercase
                                tracking-[0.12em]
                                text-slate-400
                              "
                            >
                              <span
                                className="
                                  h-px
                                  flex-1
                                  bg-slate-200
                                "
                              />

                              <span>
                                or use your work identity
                              </span>

                              <span
                                className="
                                  h-px
                                  flex-1
                                  bg-slate-200
                                "
                              />
                            </div>


                            <div
                              className="
                                mt-4
                                grid
                                gap-3
                                sm:grid-cols-2
                              "
                            >
                              {
                                identityProviders.map(
                                  (provider) => {

                                    const label =
                                      IDENTITY_PROVIDER_LABELS[
                                        provider
                                      ];


                                    return (

                                      <button
                                        key={provider}
                                        type="button"
                                        aria-label={
                                          `Continue with ${label}`
                                        }
                                        disabled={
                                          loading
                                          ||
                                          Boolean(
                                            identityAction
                                          )
                                          ||
                                          Boolean(
                                            registrationAction
                                          )
                                        }
                                        onClick={() =>
                                          handleIdentityStart(
                                            provider
                                          )
                                        }
                                        className="
                                          flex
                                          min-h-11
                                          items-center
                                          justify-center
                                          gap-2
                                          rounded-xl
                                          border
                                          border-slate-200
                                          bg-white
                                          px-3
                                          py-2.5
                                          text-xs
                                          font-semibold
                                          text-slate-700
                                          shadow-sm
                                          transition
                                          hover:border-slate-300
                                          hover:bg-slate-50
                                          disabled:cursor-not-allowed
                                          disabled:opacity-60
                                        "
                                      >
                                        <span
                                          aria-hidden="true"
                                          className="
                                            flex
                                            h-6
                                            w-6
                                            items-center
                                            justify-center
                                            rounded-md
                                            border
                                            border-slate-200
                                            bg-slate-50
                                            text-[10px]
                                            font-black
                                            text-slate-700
                                          "
                                        >
                                          {
                                            provider ===
                                              "google"
                                              ? "G"
                                              : "M"
                                          }
                                        </span>

                                        <span>
                                          {
                                            identityAction ===
                                              provider
                                              ? "Connecting..."
                                              : (
                                                  `Continue with ${label}`
                                                )
                                          }
                                        </span>
                                      </button>

                                    );

                                  }
                                )
                              }
                            </div>
                          </div>

                        )
                      }
                    </>

                  )
                : (

                    <>
                      {
                        registrationBlocked
                          ? (

                              <button
                                type="button"
                                onClick={() =>
                                  switchMode(
                                    "signin"
                                  )
                                }
                                className="
                                  flex
                                  w-full
                                  items-center
                                  justify-center
                                  gap-2
                                  rounded-xl
                                  border
                                  border-slate-200
                                  bg-white
                                  px-4
                                  py-3
                                  text-sm
                                  font-semibold
                                  text-slate-700
                                  transition
                                  hover:bg-slate-50
                                "
                              >
                                Back to sign in
                              </button>

                            )
                          : (

                              <div
                                className="
                                  space-y-4
                                "
                              >
                                <div>
                                  <label
                                    htmlFor="oneuch-organization"
                                    className="
                                      mb-1.5
                                      block
                                      text-xs
                                      font-semibold
                                      text-slate-700
                                    "
                                  >
                                    Company or workspace name
                                  </label>

                                  <input
                                    id="oneuch-organization"
                                    type="text"
                                    autoComplete="organization"
                                    maxLength={255}
                                    value={
                                      organizationName
                                    }
                                    onChange={
                                      (event) =>
                                        setOrganizationName(
                                          event.target.value
                                        )
                                    }
                                    placeholder="Your organization"
                                    className="
                                      w-full
                                      rounded-xl
                                      border
                                      border-slate-200
                                      bg-white
                                      px-3
                                      py-3
                                      text-sm
                                      text-slate-900
                                      outline-none
                                      placeholder:text-slate-400
                                      focus:border-slate-400
                                      focus:ring-2
                                      focus:ring-slate-100
                                    "
                                  />
                                </div>


                                <label
                                  className="
                                    flex
                                    cursor-pointer
                                    items-start
                                    gap-3
                                    rounded-xl
                                    border
                                    border-slate-200
                                    bg-slate-50
                                    p-3
                                  "
                                >
                                  <input
                                    type="checkbox"
                                    checked={
                                      registrationAcknowledged
                                    }
                                    onChange={
                                      (event) =>
                                        setRegistrationAcknowledged(
                                          event.target.checked
                                        )
                                    }
                                    className="
                                      mt-0.5
                                      h-4
                                      w-4
                                      rounded
                                      border-slate-300
                                    "
                                  />

                                  <span
                                    className="
                                      text-xs
                                      leading-5
                                      text-slate-600
                                    "
                                  >
                                    I acknowledge the One UCH Privacy Notice
                                    {
                                      registrationConfig
                                        .privacy_notice_version
                                      && (
                                        <>
                                          {" "}
                                          (
                                          {
                                            registrationConfig
                                              .privacy_notice_version
                                          }
                                          )
                                        </>
                                      )
                                    }
                                    {" "}and Terms
                                    {
                                      registrationConfig
                                        .terms_version
                                      && (
                                        <>
                                          {" "}
                                          (
                                          {
                                            registrationConfig
                                              .terms_version
                                          }
                                          )
                                        </>
                                      )
                                    }
                                    {" "}for this access request.
                                  </span>
                                </label>


                                <div
                                  className="
                                    rounded-xl
                                    border
                                    border-sky-100
                                    bg-sky-50
                                    px-3
                                    py-2.5
                                    text-[11px]
                                    leading-5
                                    text-sky-800
                                  "
                                >
                                  Google or Microsoft is used only to verify your identity here.
                                  Mailbox access is requested separately after workspace approval.
                                </div>


                                <div
                                  className="
                                    grid
                                    gap-3
                                    sm:grid-cols-2
                                  "
                                >
                                  {
                                    registrationProviders.map(
                                      (provider) => {

                                        const label =
                                          IDENTITY_PROVIDER_LABELS[
                                            provider
                                          ];


                                        return (

                                          <button
                                            key={provider}
                                            type="button"
                                            disabled={
                                              Boolean(
                                                registrationAction
                                              )
                                              ||
                                              Boolean(
                                                identityAction
                                              )
                                              ||
                                              loading
                                            }
                                            onClick={() =>
                                              handleRegistrationStart(
                                                provider
                                              )
                                            }
                                            className="
                                              flex
                                              min-h-11
                                              items-center
                                              justify-center
                                              gap-2
                                              rounded-xl
                                              bg-slate-950
                                              px-3
                                              py-2.5
                                              text-xs
                                              font-semibold
                                              text-white
                                              transition
                                              hover:bg-slate-800
                                              disabled:cursor-not-allowed
                                              disabled:opacity-60
                                            "
                                          >
                                            <span
                                              aria-hidden="true"
                                              className="
                                                flex
                                                h-6
                                                w-6
                                                items-center
                                                justify-center
                                                rounded-md
                                                bg-white/10
                                                text-[10px]
                                                font-black
                                                text-white
                                              "
                                            >
                                              {
                                                provider ===
                                                  "google"
                                                  ? "G"
                                                  : "M"
                                              }
                                            </span>

                                            <span>
                                              {
                                                registrationAction ===
                                                  provider
                                                  ? "Starting..."
                                                  : (
                                                      `Request with ${label}`
                                                    )
                                              }
                                            </span>
                                          </button>

                                        );

                                      }
                                    )
                                  }
                                </div>
                              </div>

                            )
                      }
                    </>

                  )
            }


            <div
              className="
                mt-6
                flex
                items-center
                justify-center
                gap-2
                text-[11px]
                text-slate-400
              "
            >
              <ShieldCheck
                size={13}
              />

              {
                authMode ===
                  "request"
                  ? "Approval required before workspace access"
                  : "Protected workspace access"
              }
            </div>
          </div>
        </div>
      </section>
    </div>
  );

}
