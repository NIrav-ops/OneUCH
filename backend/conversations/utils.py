import re

def normalize_subject(subject: str) -> str:
    if not subject:
        return ""

    subject = subject.lower().strip()
    subject = re.sub(r'^(re:|fwd:|fw:)\s*', '', subject, flags=re.IGNORECASE)
    return subject.strip()
