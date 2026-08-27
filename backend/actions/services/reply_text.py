import re


_GMAIL_QUOTE_LINE = re.compile(
    r"(?i)(?:^|\s)"
    r"On\s+"
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),"
    r"\s+.+?"
    r"\s+wrote:\s*"
)

_HEADER_QUOTE_LINE = re.compile(
    r"(?im)^From:\s.+$"
)


def extract_new_reply_text(text):
    """
    Return only the newly-written portion of an email reply.

    Handles conservative common reply boundaries, including
    Gmail quote markers that may be flattened onto one line.
    """

    value = (text or "").strip()

    if not value:
        return ""

    cut_positions = []

    gmail_match = _GMAIL_QUOTE_LINE.search(
        value
    )

    if gmail_match:
        cut_positions.append(
            gmail_match.start()
        )

    header_match = _HEADER_QUOTE_LINE.search(
        value
    )

    if header_match:
        cut_positions.append(
            header_match.start()
        )

    quoted_index = value.find(
        "\n>"
    )

    if quoted_index >= 0:
        cut_positions.append(
            quoted_index
        )

    if not cut_positions:
        return value

    return value[
        :min(cut_positions)
    ].strip()
