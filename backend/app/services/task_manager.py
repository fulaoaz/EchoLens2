"""APScheduler-backed task manager — persistent async tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4

TaskStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


@dataclass
class Task:
    id: str = field(default_factory=lambda: uuid4().hex)
    kind: str = "generic"
    status: TaskStatus = "pending"
    progress: float = 0.0
    message: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    payload: dict = field(default_factory=dict)


class TaskManager:
    """In-memory MVP — APScheduler integration arrives in M1."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create(self, kind: str, payload: dict | None = None) -> Task:
        t = Task(kind=kind, payload=payload or {})
        self._tasks[t.id] = t
        return t

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update(self, task_id: str, **fields: object) -> None:
        t = self._tasks.get(task_id)
        if not t:
            return
        for k, v in fields.items():
            setattr(t, k, v)
        t.updated_at = datetime.utcnow()

    def list(self) -> list[Task]:
        return list(self._tasks.values())


_manager = TaskManager()


def get_manager() -> TaskManager:
    return _manager


__all__ = ["Task", "TaskManager", "TaskStatus", "get_manager"]
