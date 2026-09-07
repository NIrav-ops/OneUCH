export const EMAIL_PATTERN =
  /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/i;


export function normalizeRecipient(
  value
) {

  if (!value) {
    return null;
  }


  const email = String(
    value.email || ""
  )
    .trim()
    .toLowerCase();


  if (
    !email
    ||
    !EMAIL_PATTERN.test(
      email
    )
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


export function parseRecipientString(
  value
) {

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
      !candidate
      ||
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
