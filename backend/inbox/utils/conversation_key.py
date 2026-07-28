from inbox.utils.threading import normalize_subject


def generate_conversation_key(platform, thread_id, subject, sender):

    normalized_subject = normalize_subject(subject)

    if thread_id:
        return f"{platform}_{thread_id}"

    return f"{normalized_subject}_{sender}"