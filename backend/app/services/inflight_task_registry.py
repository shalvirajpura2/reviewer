import asyncio
from collections.abc import Callable
from typing import Generic, TypeVar


result_type = TypeVar("result_type")


class InflightTaskRegistry(Generic[result_type]):
    def __init__(self) -> None:
        self.inflight_tasks: dict[str, asyncio.Task[result_type]] = {}
        self.inflight_lock = asyncio.Lock()

    async def get_or_create(
        self,
        cache_key: str,
        task_factory: Callable[[], asyncio.Task[result_type]],
    ) -> tuple[asyncio.Task[result_type], bool]:
        async with self.inflight_lock:
            inflight_task = self.inflight_tasks.get(cache_key)
            is_owner = inflight_task is None
            if is_owner:
                inflight_task = task_factory()
                self.inflight_tasks[cache_key] = inflight_task

        return inflight_task, is_owner

    async def release(self, cache_key: str, inflight_task: asyncio.Task[result_type], is_owner: bool) -> None:
        if not is_owner:
            return

        async with self.inflight_lock:
            if self.inflight_tasks.get(cache_key) is inflight_task:
                self.inflight_tasks.pop(cache_key, None)