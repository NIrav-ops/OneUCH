def build_reply_prompt(messages, tone="professional"):
    conversation_text = ""

    for msg in messages:
        role = "Sender" if msg.direction == "in" else "You"
        conversation_text += f"{role}: {msg.body}\n\n"

    return f"""
You are an email assistant.
Tone: {tone}

Conversation:
{conversation_text}

Write a suitable reply. Do NOT send email. Suggest only.
"""
