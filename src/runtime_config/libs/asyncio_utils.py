import asyncio
import typing as t


def periodic_task(
    func: t.Callable[..., t.Awaitable[None]], callback_time: float
) -> asyncio.Task:  # type: ignore[type-arg]
    async def wrapper() -> None:
        while True:
            await asyncio.sleep(callback_time)
            await func()

    return asyncio.create_task(wrapper())
