import requests
from oauth_tokens.services import get_valid_oauth_token


def send_outlook_reply(user, to_email, subject, body):
    token = get_valid_oauth_token(user, "microsoft")

    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
        },
        json={
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body,
                },
                "toRecipients": [
                    {"emailAddress": {"address": to_email}}
                ],
            }
        },
    )

    if response.status_code >= 400:
        raise Exception("Microsoft Graph sendMail failed")
