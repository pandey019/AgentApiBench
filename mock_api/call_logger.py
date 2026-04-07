from typing import List, Dict, Any
from threading import Lock


class CallLogger:
    """Thread-safe call logger for grading."""

    def __init__(self):
        self._calls: List[Dict[str, Any]] = []
        self._lock = Lock()

    def log(self, call: Dict[str, Any]):
        with self._lock:
            self._calls.append(call)

    def get_calls(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._calls)

    def clear(self):
        with self._lock:
            self._calls.clear()
