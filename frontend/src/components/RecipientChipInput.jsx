import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import axios from "../axiosConfig";


const EMAIL_PATTERN =
  /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/i;


function normalizeRecipient(value) {

  if (!value) {
    return null;
  }


  const email = String(
    value.email || ""
  )
    .trim()
    .toLowerCase();


  if (
    !email ||
    !EMAIL_PATTERN.test(email)
  ) {
    return null;
  }


  return {
    email,
    name: String(
      value.name || ""
    ).trim(),
  };

}


export function parseRecipientString(value) {

  const source = String(
    value || ""
  ).trim();


  if (!source) {
    return [];
  }


  const recipients = [];

  const seen = new Set();


  for (
    const rawPart
    of source
      .replace(/;/g, ",")
      .split(",")
  ) {

    const part =
      rawPart.trim();


    if (!part) {
      continue;
    }


    const namedMatch =
      part.match(
        /^(.*?)<([^<>]+)>$/
      );


    const candidate =
      normalizeRecipient(
        namedMatch
          ? {
              name:
                namedMatch[1]
                  .trim()
                  .replace(
                    /^["']|["']$/g,
                    ""
                  ),

              email:
                namedMatch[2],
            }
          : {
              name: "",
              email: part,
            }
      );


    if (
      !candidate ||
      seen.has(
        candidate.email
      )
    ) {
      continue;
    }


    seen.add(
      candidate.email
    );


    recipients.push(
      candidate
    );

  }


  return recipients;

}


export function serializeRecipients(
  recipients
) {

  if (
    !Array.isArray(
      recipients
    )
  ) {
    return "";
  }


  return recipients
    .map(
      (recipient) =>
        String(
          recipient?.email || ""
        )
          .trim()
          .toLowerCase()
    )
    .filter(Boolean)
    .join(", ");

}


export default function RecipientChipInput({
  label = "To",
  value = [],
  onChange,
  placeholder = "Type a name or email",
}) {

  const recipients =
    Array.isArray(value)
      ? value
      : [];


  const [query, setQuery] =
    useState("");

  const [
    suggestions,
    setSuggestions,
  ] = useState([]);

  const [
    dropdownOpen,
    setDropdownOpen,
  ] = useState(false);

  const [
    activeIndex,
    setActiveIndex,
  ] = useState(-1);

  const [loading, setLoading] =
    useState(false);


  const selectedEmails =
    useMemo(
      () =>
        new Set(
          recipients
            .map(
              (recipient) =>
                String(
                  recipient?.email || ""
                )
                  .trim()
                  .toLowerCase()
            )
            .filter(Boolean)
        ),
      [recipients]
    );


  const loadSuggestions =
    useCallback(
      async (term) => {

        try {

          setLoading(true);


          const response =
            await axios.get(
              "/api/inbox/recipient-suggestions/",
              {
                params: {
                  q:
                    String(
                      term || ""
                    ).trim(),

                  limit: 8,
                },
              }
            );


          const results =
            (
              response.data
                ?.results || []
            )
              .map(
                normalizeRecipient
              )
              .filter(Boolean)
              .filter(
                (recipient) =>
                  !selectedEmails.has(
                    recipient.email
                  )
              );


          setSuggestions(
            results
          );


          setActiveIndex(
            results.length > 0
              ? 0
              : -1
          );

        } catch (err) {

          console.error(
            "Recipient suggestion error:",
            err
          );


          setSuggestions([]);

          setActiveIndex(-1);

        } finally {

          setLoading(false);

        }

      },
      [selectedEmails]
    );


  useEffect(() => {

    if (!dropdownOpen) {
      return undefined;
    }


    const timer =
      window.setTimeout(
        () => {
          loadSuggestions(
            query
          );
        },
        180
      );


    return () => {
      window.clearTimeout(
        timer
      );
    };

  }, [
    dropdownOpen,
    loadSuggestions,
    query,
  ]);


  const commitRecipients =
    (nextRecipients) => {

      if (
        typeof onChange
        === "function"
      ) {
        onChange(
          nextRecipients
        );
      }

    };


  const addRecipient =
    (candidate) => {

      const normalized =
        normalizeRecipient(
          candidate
        );


      if (!normalized) {
        return false;
      }


      if (
        selectedEmails.has(
          normalized.email
        )
      ) {

        setQuery("");

        return true;
      }


      commitRecipients([
        ...recipients,
        normalized,
      ]);


      setQuery("");

      setSuggestions([]);

      setActiveIndex(-1);

      setDropdownOpen(true);


      return true;

    };


  const addFreeformQuery = () => {

    const parsed =
      parseRecipientString(
        query
      );


    if (parsed.length === 0) {
      return false;
    }


    const next = [
      ...recipients,
    ];


    const seen = new Set(
      selectedEmails
    );


    for (
      const recipient
      of parsed
    ) {

      if (
        seen.has(
          recipient.email
        )
      ) {
        continue;
      }


      seen.add(
        recipient.email
      );


      next.push(
        recipient
      );

    }


    commitRecipients(
      next
    );


    setQuery("");

    setSuggestions([]);

    setActiveIndex(-1);


    return true;

  };


  const removeRecipient =
    (email) => {

      commitRecipients(
        recipients.filter(
          (recipient) =>
            String(
              recipient.email || ""
            ).toLowerCase()
            !==
            String(
              email || ""
            ).toLowerCase()
        )
      );

    };


  const handleKeyDown =
    (event) => {

      if (
        event.key
        === "ArrowDown"
      ) {

        event.preventDefault();

        setDropdownOpen(true);


        setActiveIndex(
          (current) => {

            if (
              suggestions.length
              === 0
            ) {
              return -1;
            }


            return (
              current + 1
            )
              %
              suggestions.length;

          }
        );


        return;
      }


      if (
        event.key
        === "ArrowUp"
      ) {

        event.preventDefault();

        setDropdownOpen(true);


        setActiveIndex(
          (current) => {

            if (
              suggestions.length
              === 0
            ) {
              return -1;
            }


            if (
              current <= 0
            ) {
              return (
                suggestions.length
                - 1
              );
            }


            return (
              current - 1
            );

          }
        );


        return;
      }


      if (
        event.key === "Enter"
        ||
        event.key === "Tab"
      ) {

        const activeSuggestion =
          (
            query.trim()
            &&
            dropdownOpen
            &&
            activeIndex >= 0
          )
            ? suggestions[
                activeIndex
              ]
            : null;


        if (activeSuggestion) {

          event.preventDefault();

          addRecipient(
            activeSuggestion
          );

          return;
        }


        if (
          query.trim()
          &&
          addFreeformQuery()
        ) {

          event.preventDefault();

          return;
        }

      }


      if (
        event.key === ","
        ||
        event.key === ";"
      ) {

        if (query.trim()) {

          event.preventDefault();

          addFreeformQuery();

        }


        return;
      }


      if (
        event.key === "Backspace"
        &&
        !query
        &&
        recipients.length > 0
      ) {

        event.preventDefault();


        commitRecipients(
          recipients.slice(
            0,
            -1
          )
        );


        return;
      }


      if (
        event.key === "Escape"
      ) {

        setDropdownOpen(false);

        setActiveIndex(-1);

      }

    };


  return (

    <div className="relative">

      <div
        className="
          flex min-h-12
          items-start gap-2
          rounded-xl
          border border-slate-300
          bg-white px-3 py-2
          transition
          focus-within:border-slate-500
          focus-within:ring-2
          focus-within:ring-slate-200
        "
      >

        <div
          className="
            pt-1 text-xs
            font-semibold
            uppercase
            tracking-wide
            text-slate-500
          "
        >
          {label}
        </div>


        <div
          className="
            flex min-w-0
            flex-1 flex-wrap
            items-center gap-1.5
          "
        >

          {recipients.map(
            (recipient) => (

              <div
                key={
                  recipient.email
                }
                className="
                  flex max-w-full
                  items-center gap-1.5
                  rounded-full
                  border border-slate-200
                  bg-slate-100
                  px-2.5 py-1
                  text-xs
                  text-slate-800
                "
              >

                <span
                  className="max-w-52 truncate"
                  title={
                    recipient.email
                  }
                >

                  {recipient.name
                    ? (
                        <>
                          <span
                            className="font-medium"
                          >
                            {
                              recipient.name
                            }
                          </span>

                          <span
                            className="
                              ml-1
                              text-slate-500
                            "
                          >
                            {
                              recipient.email
                            }
                          </span>
                        </>
                      )
                    : recipient.email}

                </span>


                <button
                  type="button"
                  aria-label={
                    `Remove ${recipient.email}`
                  }
                  onClick={() =>
                    removeRecipient(
                      recipient.email
                    )
                  }
                  className="
                    rounded-full
                    px-1
                    text-slate-400
                    hover:bg-slate-200
                    hover:text-slate-800
                  "
                >
                  ?
                </button>

              </div>

            )
          )}


          <input
            type="text"
            value={query}
            placeholder={
              recipients.length === 0
                ? placeholder
                : ""
            }
            onChange={(event) => {

              setQuery(
                event.target.value
              );

              setDropdownOpen(
                true
              );

            }}
            onFocus={() => {

              setDropdownOpen(
                true
              );

            }}
            onBlur={() => {

              window.setTimeout(
                () => {
                  setDropdownOpen(
                    false
                  );
                },
                120
              );

            }}
            onKeyDown={
              handleKeyDown
            }
            className="
              min-w-36
              flex-1 border-0
              bg-transparent
              py-1 text-sm
              text-slate-900
              outline-none
              placeholder:text-slate-400
            "
            autoComplete="off"
          />

        </div>

      </div>


      {dropdownOpen && (

        <div
          className="
            absolute left-0
            right-0 top-full
            z-50 mt-1
            overflow-hidden
            rounded-xl
            border border-slate-200
            bg-white
            shadow-xl
          "
        >

          <div
            className="
              border-b
              border-slate-100
              px-3 py-2
              text-[11px]
              font-medium
              uppercase
              tracking-wide
              text-slate-400
            "
          >
            Communication history
          </div>


          {loading ? (

            <div
              className="
                px-3 py-3
                text-sm
                text-slate-500
              "
            >
              Finding recipients...
            </div>

          ) : suggestions.length > 0 ? (

            <div
              className="
                max-h-64
                overflow-y-auto
                py-1
              "
            >

              {suggestions.map(
                (
                  suggestion,
                  index
                ) => (

                  <button
                    key={
                      suggestion.email
                    }
                    type="button"
                    onMouseDown={(
                      event
                    ) => {

                      event.preventDefault();

                      addRecipient(
                        suggestion
                      );

                    }}
                    className={`
                      flex w-full
                      items-center
                      justify-between
                      gap-3 px-3 py-2
                      text-left
                      ${
                        index
                        === activeIndex
                          ? "bg-slate-100"
                          : "bg-white hover:bg-slate-50"
                      }
                    `}
                  >

                    <span
                      className="
                        min-w-0
                        flex-1
                      "
                    >

                      <span
                        className="
                          block truncate
                          text-sm
                          font-medium
                          text-slate-900
                        "
                      >
                        {
                          suggestion.name
                          ||
                          suggestion.email
                        }
                      </span>


                      {suggestion.name && (

                        <span
                          className="
                            block truncate
                            text-xs
                            text-slate-500
                          "
                        >
                          {
                            suggestion.email
                          }
                        </span>

                      )}

                    </span>


                    <span
                      className="
                        shrink-0
                        text-[11px]
                        text-slate-400
                      "
                    >
                      Select
                    </span>

                  </button>

                )
              )}

            </div>

          ) : query.trim() ? (

            <div
              className="
                px-3 py-3
                text-sm
                text-slate-500
              "
            >

              {EMAIL_PATTERN.test(
                query.trim()
              )
                ? "Press Enter to add this email."
                : "No matching recipient found."}

            </div>

          ) : (

            <div
              className="
                px-3 py-3
                text-sm
                text-slate-500
              "
            >
              Start typing a name or email.
            </div>

          )}

        </div>

      )}

    </div>

  );

}
