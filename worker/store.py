from abc import ABC, abstractmethod
import os
import json


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
    def __init__(self, persist_path: str = None):
        import threading
        self._tasks: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            try:
                with open(persist_path, "r", encoding="utf-8") as f:
                    for t in json.load(f):
                        # Mark any previously running tasks as failed (server crashed)
                        if t["status"] in ("running", "pending"):
                            t["status"] = "failed"
                            t["stderr"] = t.get("stderr", "") + "\nServer restarted"
                        self._tasks[t["id"]] = t
            except Exception:
                pass

    def _save(self):
        if not self._persist_path:
            return
        try:
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(list(self._tasks.values()), f, default=str)
        except Exception:
            pass

    def create(self, task: dict) -> dict:
        with self._lock:
            self._tasks[task["id"]] = task
            self._save()
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
                self._save()
