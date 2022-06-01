# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
import abc
import typing as t

from tlab.google import credentials


class AbstractAPI(abc.ABC):

    @abc.abstractmethod
    def __init__(
        self,
        credentials: credentials.Credentials,
        version: str,
        *args: t.Any,
        **kwargs: t.Any
    ) -> None:
        """
        Parameters
        ----------
        credentials : tlab.google.credentials.Credentials
            The credentials for Google API.
        version : str
            The version of Google API
        """

    @property
    @abc.abstractmethod
    def service_name(self) -> str:
        """The service name of Google API."""
