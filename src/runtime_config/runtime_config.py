from __future__ import annotations

import copy
import os
import typing as t
from logging import getLogger
from types import TracebackType

from runtime_config import sources
from runtime_config.converters import converters_map
from runtime_config.exceptions import InstanceNotFound
from runtime_config.sources.runtime_config_server import BaseSource

logger = getLogger(__name__)

_instance = {}

SettingsType = t.Dict[str, t.Any]


class RuntimeConfig:
    def __init__(self, init_settings: SettingsType, source: BaseSource) -> None:
        self._init_settings: SettingsType = init_settings
        self._settings: SettingsType = {}

        self._source = source

    @staticmethod
    async def create(init_settings: t.Dict[str, t.Any], source: BaseSource | None = None) -> RuntimeConfig:
        if source is None:
            host = os.environ.get('RUNTIME_CONFIG_HOST')
            service_name = os.environ.get('RUNTIME_CONFIG_SERVICE_NAME')
            if host is None or service_name is None:
                raise ValueError(
                    'Define RUNTIME_CONFIG_HOST and RUNTIME_CONFIG_SERVICE_NAME environment variables or initialize '
                    'source manually and pass it to create method.'
                )
            source = sources.RuntimeConfigServer(host=host, service_name=service_name)

        inst = RuntimeConfig(init_settings=init_settings, source=source)
        _instance['inst'] = inst
        await inst.refresh()
        return inst

    async def refresh(self) -> None:
        await self._refresh_from_runtime_config_server()

    async def _refresh_from_runtime_config_server(self) -> None:
        new_settings = copy.deepcopy(self._init_settings)

        for record in await self._source.get_settings():
            if record.disable:
                continue

            try:
                # TODO реализовать парсинг сложного названия настройки, когда там будет зашито в какой уровень
                #  вложенности вставить
                new_settings[record.name] = converters_map[record.value_type](record.value)
            except Exception:
                logger.warning(
                    "An unexpected error occurred while converting the setting. name=%s", record.value, exc_info=True
                )

        self._settings = new_settings

    async def close(self) -> None:
        await self._source.close()
        _instance.pop('inst')

    async def __aenter__(self) -> RuntimeConfig:
        return self

    async def __aexit__(
        self,
        exc_type: t.Optional[t.Type[BaseException]],
        exc_val: t.Optional[BaseException],
        exc_tb: t.Optional[TracebackType],
    ) -> None:
        await self.close()


def get_instance() -> RuntimeConfig:
    try:
        return _instance['inst']
    except KeyError:
        raise InstanceNotFound('RuntimeConfig')
