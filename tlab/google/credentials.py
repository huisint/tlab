# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
from __future__ import annotations
import os

from google.auth.transport import requests
from google.oauth2 import credentials
from google_auth_oauthlib import flow


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
CLIENT_CONFIG = {
    "installed": {
        "client_id": "629905107772-2rq0b441g8k6v428ul0hvhlp0p8pq09a.apps.googleusercontent.com",
        "client_secret": "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",
        "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://accounts.google.com/o/oauth2/token",
    }
}


class Credentials:
    _credentials: credentials.Credentials

    def __init__(self, credentials: credentials.Credentials) -> None:
        self._credentials = credentials

    @classmethod
    def new(
        cls,
        *,
        client_id: str = "",
        client_secret: str = "",
        run_local_server: bool = True
    ) -> Credentials:
        """
        Create a new Credentials instance for Google API.

        Parameters
        ----------
        client_id : str
            The client ID of the GCP project.
        client_secret : str
            The client secret of the GCP project.
        run_local_server : bool
            If true, a local server runs for the authorization flow.
            Otherwise, the user manually enters the authorization code instead.

        Returns
        -------
        tlab.google.credentials.Credentials
            The new credentials.
        """
        client_config = CLIENT_CONFIG.copy()
        if client_id:
            client_config["installed"]["client_id"] = client_id
        if client_secret:
            client_config["installed"]["client_secret"] = client_secret
        _flow = flow.InstalledAppFlow.from_client_config(client_config, SCOPES)
        if run_local_server:
            creds = _flow.run_local_server()
        else:
            creds = _flow.run_console()
        return cls(creds)

    @classmethod
    def from_file(cls, filename: str | os.PathLike[str]) -> Credentials:
        """
        Create a Credentials instance for Google API from an authorized user json file.

        Parameters
        ----------
        filename : str | os.PathLike[str]
            The path to the authorized user json file.

        Returns
        -------
        tlab.google.credentials.Credentials
            The constructed credentials.

        Raises
        ------
        ValueError
            If the constructed credentials is invalid.
        """
        creds = credentials.Credentials.from_authorized_user_file(filename, SCOPES)
        if not creds.valid:
            if creds.refresh_token:
                creds.refresh(requests.Request())
            else:
                raise ValueError("The credentials is not valid and has no refresh token")
        return cls(creds)

    def save(self, filename: str | os.PathLike[str]) -> None:
        """
        Save a Credentials instance as a json file.

        Parameters
        ----------
        filename : str | os.PathLike[str]
            The path to save the credentials.
        """
        with open(filename, "w") as f:
            f.write(self._credentials.to_json())

    def refresh(self) -> None:
        """
        Refresh the access token.
        """
        self._credentials.refresh(requests.Request())
