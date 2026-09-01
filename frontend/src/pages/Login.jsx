import {
  useState,
} from "react";

import {
  ArrowRight,
  Check,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";

import axios from "../axiosConfig";


const VALUE_POINTS = [
  "Unified Gmail and Microsoft 365 communication",
  "Actions, approvals and commitments from real conversations",
  "Attention, accountability and execution in one workspace",
];


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


        const response =
          await axios.post(
            "/api/auth/token/",
            {
              email:
                email.trim(),

              password:
                password,
            }
          );


        localStorage.setItem(
          "access",
          response.data.access
        );


        localStorage.setItem(
          "refresh",
          response.data.refresh
        );


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

      {/* Product narrative */}
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
                    key={
                      point
                    }
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
                      {
                        point
                      }
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
          Communication ? Intelligence ? Action ? Accountability ? Execution
        </div>
      </section>


      {/* Authentication */}
      <section
        className="
          flex
          min-h-screen
          items-center
          justify-center
          bg-slate-50
          px-5
          py-10
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
              mb-8
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
              sm:p-8
            "
          >
            <div
              className="
                mb-7
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
                <LockKeyhole
                  size={19}
                />
              </div>


              <h2
                className="
                  text-2xl
                  font-semibold
                  tracking-tight
                  text-slate-950
                "
              >
                Welcome back
              </h2>


              <p
                className="
                  mt-2
                  text-sm
                  leading-6
                  text-slate-500
                "
              >
                Sign in to your One UCH workspace.
              </p>
            </div>


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
                    value={
                      email
                    }
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
                    value={
                      password
                    }
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


              {
                error && (
                  <div
                    role="alert"
                    className="
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
                    {
                      error
                    }
                  </div>
                )
              }


              <button
                type="submit"
                disabled={
                  loading
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
                  !loading && (
                    <ArrowRight
                      size={16}
                    />
                  )
                }
              </button>
            </form>


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

              Protected workspace access
            </div>
          </div>
        </div>
      </section>
    </div>
  );

}
