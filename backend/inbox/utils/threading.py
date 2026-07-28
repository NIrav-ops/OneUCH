import re


def normalize_subject(subject: str):

    if not subject:
        return ""

    subject = subject.lower()

    # remove reply prefixes
    subject = re.sub(r"^(re:|fwd:|fw:)\s*", "", subject)

    # remove extra spaces
    subject = re.sub(r"\s+", " ", subject)

    return subject.strip()