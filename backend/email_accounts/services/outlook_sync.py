import requests
from oauth_tokens.services import get_valid_oauth_token


def fetch_outlook_messages(user, top=20):
    token = get_valid_oauth_token(user, "microsoft")

    resp = requests.get(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": f"Bearer {token.access_token}"},
        params={"$top": top},
    ).json()

    return resp.get("value", [])
