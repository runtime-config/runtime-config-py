import json
import typing as t

from runtime_config.enums.setting_value_type import SettingValueType


def convert_bool(value: str) -> bool:
    if value in ('true', 'True', '1'):
        return True
    if value in ('false', 'False', '0'):
        return False
    raise ValueError('Received value could not be converted to a bool')


converters_map: t.Dict[SettingValueType, t.Callable[[t.Any], t.Any]] = {
    SettingValueType.str: lambda value: value,
    SettingValueType.int: int,
    SettingValueType.bool: convert_bool,
    SettingValueType.null: lambda value: None,
    SettingValueType.json: json.loads,
}
