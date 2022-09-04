from __future__ import annotations

import typing as t
from abc import ABC
from logging import getLogger
from types import TracebackType
from urllib.parse import urljoin

import aiohttp
import pydantic

from runtime_config.entities.runtime_setting_server import Setting
from runtime_config.exceptions import NotValidResponseError

logger = getLogger(__name__)

SettingsType = t.Dict[str, t.Any]


class BaseSource(ABC):
    async def get_settings(self) -> t.List[Setting]:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class RuntimeConfigServer(BaseSource):
    def __init__(self, host: str, service_name: str) -> None:
        self.url = urljoin(host, f'/get_settings/{service_name}/')
        self._http_client = aiohttp.ClientSession()

    async def get_settings(self) -> t.List[Setting]:
        resp = await self._http_client.get(url=self.url)
        try:
            return [Setting(**row) for row in await resp.json()]
        except pydantic.ValidationError:
            raise NotValidResponseError(
                'Server returned an invalid response. Check the compatibility of the server that stores the settings '
                'with the current version of the library.'
            )

    async def close(self) -> None:
        await self._http_client.close()

    async def __aenter__(self) -> RuntimeConfigServer:
        return self

    async def __aexit__(
        self,
        exc_type: t.Optional[t.Type[BaseException]],
        exc_val: t.Optional[BaseException],
        exc_tb: t.Optional[TracebackType],
    ) -> None:
        await self.close()
