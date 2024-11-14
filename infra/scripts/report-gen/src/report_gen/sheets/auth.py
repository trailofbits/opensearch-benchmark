"""Functions for authenticating with the google sheets API."""

import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Limit access to files created by this app
# See: https://developers.google.com/identity/protocols/oauth2/scopes#sheets
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def authenticate(credential_path: Path | None, token_path: Path) -> Credentials | None:
    """Authenticate with Google API.

    If a credentials file is passed, create a new token at the provided path and use it to authenticate.
    If no credentials file is passed, use the token at the provided path to authenticate.
    Return None if authorization fails.
    """
    if credential_path is not None:
        authenticate_from_credentials(credential_path, token_path)
    return authenticate_from_token(token_path)


def authenticate_from_credentials(credentials_file_path: Path, token_file_path: Path) -> None:
    """Authenticate a new session using a credentials file and create a token at the given path."""
    flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
    creds: Credentials = flow.run_local_server(port=0)

    with token_file_path.open("w") as token:
        token.write(creds.to_json())


def authenticate_from_token(token_file_path: Path) -> Credentials | None:
    """Restores a previously authenticated session, using a token file."""
    creds: Credentials | None = None

    if not token_file_path.exists():
        logger.error("Missing token file")
        return None

    creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)
    if not creds or not creds.valid:
        logger.error("Authentication has failed")
        return None

    return creds
