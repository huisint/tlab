# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
import base64
from email.mime import base as mimebase
import typing as t

from tlab.google import base, credentials


Message = dict[str, t.Any]


class GmailAPI(base.BaseAPI):
    _user_id: str

    def __init__(
        self,
        credentials: credentials.Credentials,
        version: str = "v1",
    ) -> None:
        super().__init__(credentials, version)
        self._user_id = "me"

    @property
    def service_name(self) -> str:
        return "gmail"

    @property
    def user_id(self) -> str:
        """The user's email address."""
        return self._user_id

    @user_id.setter
    def user_id(self, user_id: str) -> None:
        self._user_id = user_id

    def search_email(
        self,
        query: str,
        *,
        max_results: int = 100,
        page_token: str | None = None,
        label_ids: list[str] | None = None,
        include_spam_trash: bool = False,
    ) -> tuple[list[Message], str, int]:
        """
        Search the user's mailbox on Gmail.

        Parameters
        ----------
        query : str
            The same query format as the Gmail search box.
        max_results : int
            Maximum number of messages to return.
        page_token : str | None
            The page token to retrieve a specific page of results in the list.
        label_ids : list[str] | None
            The label IDs of messages to return.
        include_spam_trash : bool
            If true, messages from SPAM and TRASH are included in the results.

        Returns
        -------
        messages : list[tlab.google.gmail.Message]
            The list of messages.
            See also https://developers.google.com/gmail/api/reference/rest/v1/users.messages#Message for Message.
        next_page_token : str
            The token to retrieve the next page.
        result_size_estimate : int
            The estimated total number of results.

        See Also
        --------
        https://developers.google.com/gmail/api/reference/rest/v1/users.messages/list
        """
        result = self._service.users().messages().list(
            userId=self.user_id,
            q=query,
            maxResults=max_results,
            pageToken=page_token or "",
            labelIds=label_ids or [],
            includeSpamTrash=include_spam_trash
        ).execute()
        messages = [
            {str(key): message[key] for key in message}
            for message in result.get("messages", [])
        ]
        next_page_token = str(result.get("nextPageToken", ""))
        result_size_estimate = int(result.get("resultSizeEstimate", 0))
        return messages, next_page_token, result_size_estimate

    def get_email(
        self,
        id: str,
        *,
        format: t.Literal["minimal", "full", "raw", "metadata"] = "full"
    ) -> Message:
        """
        Get a email in the mailbox of Gmail.

        Parameters
        ----------
        id : str
            The ID of the message to retrieve.
        format : Literal["minimal", "full", "raw", "metadata"]
            The format to return the message in.
            See also https://developers.google.com/gmail/api/reference/rest/v1/Format.

        Returns
        -------
        tlab.google.gmail.Message
            See also https://developers.google.com/gmail/api/reference/rest/v1/users.messages#Message for Message.
        """
        result = self._service.users().messages().get(
            userId=self.user_id,
            id=id,
            format=format
        ).execute()
        return {str(key): result[key] for key in result}

    def send_email(
        self,
        message: mimebase.MIMEBase,
    ) -> None:
        """
        Send a email via Gmail.

        Parameters
        ----------
        message : email.mime.base.MIMEBase
            The message to send.
        """
        raw_body = base64.urlsafe_b64encode(message.as_bytes()).decode()
        self._service.users().messages().send(
            userId=self.user_id,
            body={"raw": raw_body}
        ).execute()

    def get_signature(
        self,
        *,
        address: str | None = None,
    ) -> str:
        """
        Get a signature registered on Gmail.

        Parameters
        ----------
        address : str | None
            The send-as alias to be retrieved.
            If None, the default send-as alias is retrieved.

        Returns
        -------
        str
            A HTML text of signature of the address.

        Raises
        ------
        ValueError
            If a signature for the address is not found.
        """
        response = self._service.users().settings().sendAs().list(
            userId=self.user_id,
        ).execute()
        addr_to_sendas = {
            sendas["sendAsEmail"]: sendas for sendas in response.get("sendAs", [])
        }
        if address is None:
            # Get the default send-as alias
            sendas = [sendas for sendas in addr_to_sendas.values() if sendas.get("isDefault", False)].pop()
        else:
            if address not in addr_to_sendas.keys():
                raise ValueError(f"A signature for {address} not found")
            sendas = addr_to_sendas[address]
        return str(sendas.get("signature", ""))
