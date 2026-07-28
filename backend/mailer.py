"""Send emails via Gmail API — OAuth2 (preferred) or service account."""
import base64
import logging
import os
import sys
import time
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuth2Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Minimal scope: send only, no inbox access.
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_SCOPES = [GMAIL_SCOPE]
DEFAULT_CREDS_FILE = "service-account-key.json"
TOKEN_FILE = "gmail_token.json"
LOG_PATH = os.path.join("logs", "mailer.log")


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    # Mirror logs to stdout so runs are visible in CI/console.
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def _call_with_retry(func, max_retries: int = 3):
    """Call a Gmail API function with exponential backoff."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except HttpError as e:
            last_error = e
            if e.resp.status in (429, 500, 503):
                wait = 2 ** attempt
                logging.warning(f"API attempt {attempt} failed, retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise
    raise last_error


def _build_oauth2_credentials() -> OAuth2Credentials:
    """Load OAuth2 refresh token from gmail_token.json.

    The token file is created once by running backend/oauth_setup.py.
    google-auth auto-refreshes expired access tokens during API calls.
    """
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"OAuth2 token file not found: {TOKEN_FILE}. "
            "Run 'python backend/oauth_setup.py' once to create it."
        )
    return OAuth2Credentials.from_authorized_user_file(TOKEN_FILE, scopes=GMAIL_SCOPES)


def _build_service_account_credentials(creds_file: str, sender_email: str):
    """Build delegated service-account credentials (Workspace only)."""
    credentials = service_account.Credentials.from_service_account_file(
        creds_file, scopes=GMAIL_SCOPES
    )
    return credentials.with_subject(sender_email)


def _get_credentials(sender_email: str, creds_file: str):
    """Resolve credentials: OAuth2 token → service account → fail clearly.

    Priority: gmail_token.json (OAuth2, works with @gmail.com).
    Fallback: service-account-key.json (Workspace domain-wide delegation).
    """
    if os.path.exists(TOKEN_FILE):
        logging.info("Using OAuth2 credentials from %s", TOKEN_FILE)
        return _build_oauth2_credentials()

    if os.path.exists(creds_file):
        logging.info("Using service account credentials from %s", creds_file)
        return _build_service_account_credentials(creds_file, sender_email)

    raise FileNotFoundError(
        f"No Gmail credentials found. Either:\n"
        f"  1. Run 'python backend/oauth_setup.py' to create {TOKEN_FILE} (for @gmail.com), or\n"
        f"  2. Place a service account key at {creds_file} (for Google Workspace)."
    )


def _build_message(
    sender: str,
    recipients: list,
    subject: str,
    html_body: str,
    chart_path: Optional[str] = None,
) -> dict:
    msg = MIMEMultipart("related")
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    if chart_path:
        if os.path.exists(chart_path):
            with open(chart_path, "rb") as f:
                image = MIMEImage(f.read())
            image.add_header("Content-ID", "<salespulse_chart>")
            image.add_header(
                "Content-Disposition",
                "inline",
                filename=os.path.basename(chart_path),
            )
            msg.attach(image)
        else:
            logging.warning(f"Chart path not found, sending without image: {chart_path}")

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    return {"raw": raw}


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    chart_path: Optional[str] = None,
    creds_file: Optional[str] = None,
) -> None:
    """Send an HTML email, optionally with an inline chart, via Gmail API.

    Auth flow (priority order):
    1. gmail_token.json — OAuth2 refresh token (for @gmail.com accounts).
       Created once via 'python backend/oauth_setup.py'. Auto-refreshes.
    2. service-account-key.json — Workspace domain-wide delegation.
       Requires admin to authorize the service account client ID.
    """
    setup_logging()

    sender_email = os.environ.get("SENDER_EMAIL")
    if not sender_email:
        raise ValueError("SENDER_EMAIL environment variable is required")

    # Source of truth: env var first, then explicit argument, then default filename.
    creds_file = os.environ.get("CREDS_FILE") or creds_file or DEFAULT_CREDS_FILE

    # TO_EMAIL env var takes precedence; parameter is the fallback.
    to_email = os.environ.get("TO_EMAIL") or to_email
    recipients = [addr.strip() for addr in to_email.split(",") if addr.strip()]
    if not recipients:
        raise ValueError("At least one recipient is required")

    try:
        credentials = _get_credentials(sender_email, creds_file)
        service = build("gmail", "v1", credentials=credentials)

        message = _build_message(
            sender_email, recipients, subject, html_body, chart_path
        )
        result = _call_with_retry(
            lambda: service.users()
            .messages()
            .send(userId="me", body=message)
            .execute()
        )

        logging.info(f"Email sent to {recipients} — id={result.get('id')}")
    except HttpError as e:
        logging.error(f"Failed to send email to {recipients}: {e}")
        raise
    except Exception as e:
        logging.error(f"Failed to send email to {recipients}: {e}")
        raise


if __name__ == "__main__":
    sender = os.environ.get("SENDER_EMAIL")
    recipient = os.environ.get("TO_EMAIL")

    if not sender or not recipient:
        print("Skipping send — env vars not configured")
    elif not os.path.exists(TOKEN_FILE) and not os.path.exists(DEFAULT_CREDS_FILE):
        print("Skipping send — no credentials found. Run 'python backend/oauth_setup.py' first.")
    else:
        html = """
        <html>
          <body>
            <h2>Test Email</h2>
            <p>This is a test from backend/mailer.py.</p>
          </body>
        </html>
        """
        send_email(
            to_email=recipient,
            subject="[Test] Automated Weekly Sales Report",
            html_body=html,
            chart_path=None,
        )
