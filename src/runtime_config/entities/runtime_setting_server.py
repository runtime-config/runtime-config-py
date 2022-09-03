from dataclasses import dataclass

from runtime_config.enums.setting_value_type import SettingValueType


@dataclass
class Setting:
    name: str
    value: str
    value_type: SettingValueType
    disable: bool
