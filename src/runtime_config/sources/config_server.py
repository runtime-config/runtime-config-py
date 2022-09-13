from __future__ import annotations

import os.path
import typing as t
from logging import getLogger
from types import TracebackType
from urllib.parse import urlparse

import aiohttp
import pydantic

from runtime_config.entities.runtime_setting_server import Setting
from runtime_config.exceptions import ValidationError
from runtime_config.sources.base import BaseSource

logger = getLogger(__name__)

SettingsType = t.Dict[str, t.Any]


class ConfigServerSrc(BaseSource):
    """
    Source that allows you to get settings from the runtime-config server.
    """

    def __init__(self, host: str, service_name: str) -> None:
        self._url = self._build_url(host=host, service_name=service_name)
        self._http_client = aiohttp.ClientSession()

    def _build_url(self, host: str, service_name: str) -> str:
        parsed_url = urlparse(host)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise ValueError('Invalid host url received')

        return os.path.join(host, 'get_settings', service_name)

    async def get_settings(self) -> t.List[Setting]:
        resp = await self._http_client.get(url=self._url)
        try:
            return [Setting(**row) for row in await resp.json()]
        except pydantic.ValidationError:
            raise ValidationError(
                'Server returned an invalid response. Check the compatibility of the server that stores the settings '
                'with the current version of the library.'
            )

    async def close(self) -> None:
        await self._http_client.close()

    async def __aenter__(self) -> ConfigServerSrc:
        return self

    async def __aexit__(
        self,
        exc_type: t.Optional[t.Type[BaseException]],
        exc_val: t.Optional[BaseException],
        exc_tb: t.Optional[TracebackType],
    ) -> None:
        await self.close()
