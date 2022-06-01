# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
import typing as t

from googleapiclient import discovery

from tlab.google import credentials, abstract


class BaseAPI(abstract.AbstractAPI):
    _service: t.Any

    def __init__(self, credentials: credentials.Credentials, version: str) -> None:
        self._service = discovery.build(
            serviceName=self.service_name,
            version=version,
            credentials=credentials._credentials
        )
