from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


TaskStop = Callable[[], None]


@dataclass(slots=True, frozen=True)
class TaskLease:
    kind: str
    token: int
    generation: int


@dataclass(slots=True)
class _TaskRecord:
    lease: TaskLease
    stop: TaskStop | None


class TaskCoordinator:
    """Owns long-running task identity independently from page widgets."""

    def __init__(self) -> None:
        self._next_token = 0
        self._tasks: dict[str, _TaskRecord] = {}

    def begin(
        self,
        kind: str,
        *,
        generation: int,
        stop: TaskStop | None = None,
    ) -> TaskLease | None:
        if kind in self._tasks:
            return None
        self._next_token += 1
        lease = TaskLease(kind=kind, token=self._next_token, generation=generation)
        self._tasks[kind] = _TaskRecord(lease=lease, stop=stop)
        return lease

    def is_current(self, lease: TaskLease | None) -> bool:
        if lease is None:
            return False
        record = self._tasks.get(lease.kind)
        return record is not None and record.lease == lease

    def finish(self, lease: TaskLease | None) -> bool:
        if not self.is_current(lease):
            return False
        assert lease is not None
        del self._tasks[lease.kind]
        return True

    def active(self, kind: str | None = None) -> tuple[TaskLease, ...]:
        if kind is not None:
            record = self._tasks.get(kind)
            return () if record is None else (record.lease,)
        return tuple(record.lease for record in self._tasks.values())

    def is_active(self, kind: str) -> bool:
        return bool(self.active(kind))

    def stop(self, kind: str) -> bool:
        record = self._tasks.get(kind)
        if record is None:
            return False
        if record.stop is not None:
            record.stop()
        return True

    def stop_all(self) -> None:
        for record in tuple(self._tasks.values()):
            if record.stop is not None:
                record.stop()

    def clear(self) -> None:
        self._tasks.clear()


__all__ = ["TaskCoordinator", "TaskLease"]
