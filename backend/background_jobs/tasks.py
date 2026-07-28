from oauth_tokens.models import OAuthToken
from oauth_tokens.services.refresh import (
    refresh_google_token,
    refresh_microsoft_token
)
from audit_logs.models import AuditLog


def refresh_oauth_tokens():
    tokens = OAuthToken.objects.all()

    for token in tokens:
        try:
            if token.is_expired():
                if token.provider == 'google':
                    refresh_google_token(token)
                elif token.provider == 'microsoft':
                    refresh_microsoft_token(token)

        except Exception as e:
            AuditLog.objects.create(
                user=token.user,
                action="oauth_refresh_failed",
                platform=token.provider,
                description=str(e)
            )

from email_accounts.models import EmailAccount
from email_accounts.services.imap_smtp import fetch_imap_emails
from audit_logs.models import AuditLog


def fetch_all_imap_inboxes():
    accounts = EmailAccount.objects.filter(account_type='imap', is_active=True)

    for account in accounts:
        try:
            fetch_imap_emails(
                user=account.user,
                email_account=account,
                password=None  # password requested on demand
            )
        except Exception as e:
            AuditLog.objects.create(
                user=account.user,
                action="imap_fetch_failed",
                platform="imap",
                description=str(e)
            )
