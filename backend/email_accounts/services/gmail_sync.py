import requests
from oauth_tokens.services import get_valid_oauth_token


def fetch_gmail_messages(user, max_results=20):
    token = get_valid_oauth_token(user, "google")

    resp = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers={"Authorization": f"Bearer {token.access_token}"},
        params={"maxResults": max_results},
    ).json()

    return resp.get("messages", [])


def fetch_gmail_message_detail(user, msg_id):
    token = get_valid_oauth_token(user, "google")

    resp = requests.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
        headers={"Authorization": f"Bearer {token.access_token}"},
        params={"format": "full"},
    ).json()

    return resp
