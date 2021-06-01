import asyncio


class TasksMixin:
    def __init__(self, *args, **kwargs):
        self._tasks = {}
        super().__init__(*args, **kwargs)

    def start_task(self, name: str, task):
        if name not in self._tasks:
            self._tasks[name] = asyncio.ensure_future(task)

    def end_task(self, name: str):
        task = self._tasks.pop(name)
        task.cancel()
        return task

    def end_all_tasks(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        self._tasks = {}


class AutoTasksMixin(TasksMixin):
    """Automatically hook into mount/unmount for the simple case."""

    def mount(self, *args, **kwargs):
        if hasattr(super(), "mount"):
            super().mount(*args, **kwargs)
        if hasattr(self, "update"):
            self.start_task("update", self.update(*args, **kwargs))

    def unmount(self, *args, **kwargs):
        if hasattr(super(), "unmount"):
            super().unmount(*args, **kwargs)
        self.end_all_tasks()
