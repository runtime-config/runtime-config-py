from dataclasses import dataclass

from pydantic import validate_arguments

from runtime_config.enums.setting_value_type import SettingValueType


@validate_arguments
@dataclass
class Setting:
    name: str
    value: str
    value_type: SettingValueType
    disable: bool
