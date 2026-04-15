from abc import ABC, abstractmethod


class TaskStore(ABC):
    @abstractmethod
    def create(self, task: dict) -> dict: ...

    @abstractmethod
    def get(self, task_id: str) -> dict | None: ...

    @abstractmethod
    def list(self, limit: int = 50) -> list[dict]: ...

    @abstractmethod
    def update(self, task_id: str, fields: dict) -> None: ...


class MemoryStore(TaskStore):
    def __init__(self):
        import threading
        self._tasks: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, task: dict) -> dict:
        with self._lock:
            self._tasks[task["id"]] = task
        return task

    def get(self, task_id: str) -> dict | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t["createdAt"], reverse=True)[:limit]

    def update(self, task_id: str, fields: dict) -> None:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].update(fields)
