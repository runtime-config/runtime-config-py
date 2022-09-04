from __future__ import annotations

import copy
import os
import typing as t
from logging import getLogger
from types import TracebackType

from runtime_config import sources
from runtime_config.converters import converters_map
from runtime_config.entities.runtime_setting_server import Setting
from runtime_config.exceptions import InstanceNotFound, NotValidResponseError
from runtime_config.sources.runtime_config_server import BaseSource

logger = getLogger(__name__)

_instance = {}

SettingsType = t.Dict[str, t.Any]


class RuntimeConfig:
    def __init__(self, init_settings: SettingsType, source: BaseSource) -> None:
        self._init_settings: SettingsType = init_settings
        self._settings: SettingsType = {}

        self._source = source
        self.settings_merger = SettingsMerger(init_settings=init_settings)

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
        try:
            extracted_settings = await self._source.get_settings()
        except NotValidResponseError as exc:
            logger.error(str(exc), exc_info=True)
        except Exception:
            logger.error('An unexpected error occurred while fetching new settings from the server', exc_info=True)
        else:
            self._settings = await self.settings_merger.merge(extracted_settings=extracted_settings)

    async def close(self) -> None:
        await self._source.close()
        _instance.pop('inst')

    def __getitem__(self, key: str) -> t.Any:
        return self._settings[key]

    def __getattr__(self, attr: str) -> t.Any:
        return self._settings[attr]

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


class SettingsMerger:
    def __init__(self, init_settings: SettingsType):
        self.init_settings = init_settings

    async def merge(self, extracted_settings: t.List[Setting]) -> SettingsType:
        new_settings = copy.deepcopy(self.init_settings)

        for setting in extracted_settings:
            if setting.disable:
                continue
            self._insert_new_value(new_settings=new_settings, setting=setting)

        return new_settings

    def _insert_new_value(self, new_settings: SettingsType, setting: Setting) -> None:
        try:
            new_value = converters_map[setting.value_type](setting.value)
        except Exception:
            logger.warning(
                "Failed to convert setting to required type. name=%s, value_type=%s",
                setting.name,
                setting.value_type,
                exc_info=True,
            )
            return

        try:
            target_dict, key = self._get_target_dict(new_settings, setting_name=setting.name)
            target_dict[key] = new_value
        except Exception:
            logger.warning(
                "An unexpected error occurred while inserted the setting. name=%s",
                setting.name,
                exc_info=True,
            )

    def _get_target_dict(  # type: ignore[return]
        self, new_settings: SettingsType, setting_name: str
    ) -> t.Tuple[dict[str, t.Any], str]:
        if '__' not in setting_name:
            return new_settings, setting_name
        else:
            path = setting_name.split('__')
            len_path = len(path)
            nested_dict = new_settings
            for index, current_key in enumerate(path):
                if len_path - index == 1:
                    return nested_dict, current_key
                else:
                    nested_dict = nested_dict[current_key]
