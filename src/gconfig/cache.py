from typing import Any, Callable, Dict, Optional


class CacheEntry:
    def __init__(
        self,
        typ: type,
        key: str,
        value: Any,
        change_callback_fn: Optional[Callable[[Any], None]] = None,
    ) -> None:
        self.type = typ
        self.key = key
        self.value = value
        self.change_callback_fn = change_callback_fn


class Cache:
    def __init__(self) -> None:
        self.cache: Dict[str, CacheEntry] = {}

    def set(self, cache_entry: CacheEntry) -> None:
        self.cache[cache_entry.key] = cache_entry

    def get(self, key: str) -> CacheEntry:
        return self.cache.get(key)
