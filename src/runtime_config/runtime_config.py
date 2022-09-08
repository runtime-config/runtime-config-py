from __future__ import annotations

import asyncio
import copy
import os
import typing as t
from logging import getLogger
from types import TracebackType

from runtime_config import sources
from runtime_config.converters import converters_map
from runtime_config.entities.runtime_setting_server import Setting
from runtime_config.exceptions import InitializationError, ValidationError
from runtime_config.libs.asyncio_utils import periodic_task
from runtime_config.sources.config_server import BaseSource

logger = getLogger(__name__)

_instance = {}

SettingsType = t.Dict[str, t.Any]


class RuntimeConfig:
    def __init__(self, init_settings: SettingsType, source: BaseSource, refresh_interval: float) -> None:
        self._init_settings: SettingsType = init_settings
        self._settings: SettingsType = {}

        self._source = source
        self._settings_merger = SettingsMerger(init_settings=init_settings)
        self._periodic_refresh_task: asyncio.Task[None] = periodic_task(self.refresh, callback_time=refresh_interval)

    @staticmethod
    async def create(
        init_settings: t.Dict[str, t.Any], source: BaseSource | None = None, refresh_interval: float = 10
    ) -> RuntimeConfig:
        """
        Creates and initializes an instance of the class. You should always use this method to instantiate a class.
        :param init_settings: dictionary with default settings that you can then override.
        :param source: the source from which the actual values of the variables will be retrieved.
        :param refresh_interval: the frequency with which updates will be requested from the source.
        :return: initialized class instance.
        """
        if 'inst' in _instance:
            raise InitializationError('You have already initialized the RuntimeConfig instance.')

        if source is None:
            host = os.environ.get('RUNTIME_CONFIG_HOST')
            service_name = os.environ.get('RUNTIME_CONFIG_SERVICE_NAME')
            if host is None or service_name is None:
                raise ValueError(
                    'Define RUNTIME_CONFIG_HOST and RUNTIME_CONFIG_SERVICE_NAME environment variables or initialize '
                    'source manually and pass it to create method.'
                )
            source = sources.ConfigServerSrc(host=host, service_name=service_name)

        inst = RuntimeConfig(init_settings=init_settings, source=source, refresh_interval=refresh_interval)
        _instance['inst'] = inst
        await inst.refresh()
        return inst

    async def refresh(self) -> None:
        extracted_settings = []
        try:
            extracted_settings = await self._source.get_settings()
        except ValidationError as exc:
            logger.error(str(exc), exc_info=True)
        except Exception:
            logger.error('An unexpected error occurred while fetching new settings from the server', exc_info=True)

        try:
            self._settings = await self._settings_merger.merge(extracted_settings=extracted_settings)
        except Exception:
            logger.error('An unexpected error occurred while merge settings', exc_info=True)

    def get(self, setting_name: str, default: t.Any = None) -> t.Any:
        return self._settings.get(setting_name, default)

    async def close(self) -> None:
        self._periodic_refresh_task.cancel()
        await self._source.close()
        _instance.pop('inst')

    def __getitem__(self, key: str) -> t.Any:
        return self._settings[key]

    def __getattr__(self, attr: str) -> t.Any:
        try:
            return self._settings[attr]
        except KeyError:
            raise AttributeError(f'{attr} setting not found')

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
        raise InitializationError(
            'You have not created a RuntimeConfig instance. You need to execute the RuntimeConfig.create method.'
        )


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
            target_dict, key = self._get_inner_dict(settings=new_settings, setting_name=setting.name)
        except KeyError:
            self._insert_new_value_in_inner_dict(settings=new_settings, setting_name=setting.name, value=new_value)
        else:
            target_dict[key] = new_value

    def _get_inner_dict(  # type: ignore[return]
        self, settings: SettingsType, setting_name: str
    ) -> t.Tuple[t.Dict[str, t.Any], str]:
        if '__' not in setting_name:
            return settings, setting_name
        else:
            path = setting_name.split('__')
            len_path = len(path)
            inner_dict = settings
            for index, current_key in enumerate(path):
                if len_path - index == 1:
                    return inner_dict, current_key
                else:
                    inner_dict = inner_dict[current_key]

    def _insert_new_value_in_inner_dict(self, settings: SettingsType, setting_name: str, value: t.Any) -> None:
        path = setting_name.split('__')
        last_key = path.pop(-1)

        inner_dict = settings
        for current_key in path:
            if current_key in settings:
                inner_dict = inner_dict[current_key]
            else:
                new_dict: t.Dict[t.Any, t.Any] = {}
                inner_dict[current_key] = new_dict
                inner_dict = new_dict

        inner_dict[last_key] = value
