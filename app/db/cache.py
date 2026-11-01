"""Cache kết quả truy vấn trong bộ nhớ (TTL + LRU) cho các câu hỏi lặp lại.

Key = SQL + tham số bind. Vì bộ lọc quyền theo group được đưa vào SQL/params,
hai user khác quyền sẽ có key khác nhau, không dùng chung kết quả.

Cache nằm trong process: mỗi worker uvicorn có cache riêng, mất khi restart.
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

import pandas as pd


def make_key(sql: str, params: dict[str, Any] | list | None) -> str:
    """Key ổn định: không phụ thuộc thứ tự tham số hay khoảng trắng đầu/cuối SQL."""
    payload = json.dumps({"sql": sql.strip(), "params": params}, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class QueryCache:
    def __init__(
        self,
        ttl_seconds: float,
        max_entries: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._items: OrderedDict[str, tuple[float, pd.DataFrame]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> pd.DataFrame | None:
        with self._lock:
            item = self._items.get(key)
            if item is None or item[0] <= self._clock():
                if item is not None:
                    del self._items[key]
                self.misses += 1
                return None
            self._items.move_to_end(key)
            self.hits += 1
            # Trả bản sao để code phía sau sửa DataFrame không làm hỏng cache.
            return item[1].copy()

    def set(self, key: str, df: pd.DataFrame) -> None:
        with self._lock:
            self._items[key] = (self._clock() + self.ttl_seconds, df.copy())
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = self.hits + self.misses
            return {
                "entries": len(self._items),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_pct": round(self.hits / total * 100, 2) if total else None,
                "ttl_seconds": self.ttl_seconds,
            }
