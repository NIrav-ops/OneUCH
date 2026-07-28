from oauth_tokens.services import get_valid_oauth_token
import base64
import requests
from email.mime.text import MIMEText


def send_gmail_reply(user, to_email, subject, body):
    token = get_valid_oauth_token(user, "google")

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    response = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
        },
        json={"raw": raw},
    )

    if response.status_code >= 400:
        raise Exception("Gmail API send failed")

    return response.json()
