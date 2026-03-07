from __future__ import annotations

from threading import Event


class UploadCancelled(RuntimeError):
    pass


class UploadCancellationToken:
    def __init__(self) -> None:
        self._event = Event()

    def request_stop(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self, message: str = "stopped by user") -> None:
        if self.is_cancelled():
            raise UploadCancelled(message)
