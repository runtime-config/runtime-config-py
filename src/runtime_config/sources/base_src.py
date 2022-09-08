import typing as t
from abc import ABC

from runtime_config.entities.runtime_setting_server import Setting


class BaseSource(ABC):
    async def get_settings(self) -> t.List[Setting]:
        raise NotImplementedError  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError  # pragma: no cover
