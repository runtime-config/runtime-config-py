import asyncio
import typing as t


async def periodic_callback(func: t.Callable[..., t.Any], callback_time: int) -> None:
    while True:
        await func()
        await asyncio.sleep(callback_time)
