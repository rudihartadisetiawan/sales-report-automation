"""One-time OAuth2 setup: get a refresh token for Gmail send access.

Run this ONCE interactively. It opens a browser, you log in with the
Gmail account that will SEND the reports, and grant the gmail.send scope.
The refresh token is saved to gmail_token.json for automated use.

Usage:  python backend/oauth_setup.py
"""
from __future__ import annotations

import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

# Minimal scope: send only, no inbox access.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = "gmail_token.json"
CLIENT_SECRET_FILE = "client_secret.json"


def main() -> None:
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"ERROR: {CLIENT_SECRET_FILE} not found.", file=sys.stderr)
        print("Place your OAuth Desktop client JSON in the project root.", file=sys.stderr)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES)

    # run_local_server() opens a browser → you log in → redirects to localhost
    credentials = flow.run_local_server(port=0)

    # Save refresh token for headless/automated use
    with open(TOKEN_FILE, "w") as f:
        f.write(credentials.to_json())

    print(f"[OK] Token saved to {TOKEN_FILE}")
    print("   Make sure SENDER_EMAIL env var matches the account you just authenticated with.")
    print("   Ready for automated sending via mailer.py")


if __name__ == "__main__":
    main()
