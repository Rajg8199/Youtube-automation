"""One-time YouTube OAuth helper — run on your machine to mint a refresh token.

    make youtube-auth        # or: cd apps/worker && uv run --extra youtube python -m app.youtube_auth

Reads YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET from the repo .env, opens your browser for
consent, exchanges the code for a refresh token, and writes YOUTUBE_REFRESH_TOKEN back into
.env. Needs the OAuth client to allow the loopback redirect http://localhost:<port>/ (a
"Desktop app" client does by default; for a "Web application" client add that redirect URI).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from .publishing import YOUTUBE_SCOPES

_PORT = 8765
# repo root = .../phonewala-gyan ; this file is apps/worker/app/youtube_auth.py
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _read_env(name: str) -> str:
    val = os.environ.get(name, "")
    if val:
        return val
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].split("#", 1)[0].strip()
    return ""


def _write_refresh_token(token: str) -> None:
    if not _ENV_PATH.exists():
        print(f"!! {_ENV_PATH} not found — set YOUTUBE_REFRESH_TOKEN manually:\n{token}")
        return
    text = _ENV_PATH.read_text(encoding="utf-8")
    line = f"YOUTUBE_REFRESH_TOKEN={token}"
    if re.search(r"^YOUTUBE_REFRESH_TOKEN=.*$", text, flags=re.MULTILINE):
        text = re.sub(r"^YOUTUBE_REFRESH_TOKEN=.*$", line, text, flags=re.MULTILINE)
    else:
        text += ("\n" if not text.endswith("\n") else "") + line + "\n"
    _ENV_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    client_id = _read_env("YOUTUBE_CLIENT_ID")
    client_secret = _read_env("YOUTUBE_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("!! Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env first.")
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("!! Missing deps. Run: cd apps/worker && uv sync --extra youtube")
        return 1

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"http://localhost:{_PORT}/"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=YOUTUBE_SCOPES)
    print(f">> Opening your browser for Google consent (loopback http://localhost:{_PORT}/)...")
    print("   If the app is in 'Testing' mode, sign in as a registered test user.")
    creds = flow.run_local_server(
        port=_PORT, access_type="offline", prompt="consent",
        authorization_prompt_message="Visit this URL to authorize:\n{url}",
    )
    if not creds.refresh_token:
        print("!! No refresh token returned. Revoke prior access at "
              "https://myaccount.google.com/permissions and retry (prompt=consent).")
        return 1

    _write_refresh_token(creds.refresh_token)
    print("\n✅ Refresh token saved to .env (YOUTUBE_REFRESH_TOKEN).")
    print("   Restart the worker to pick it up:  docker compose -f infra/docker-compose.yml up -d worker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
