from ast import Dict
from enum import Enum
from typing import Callable, Optional


class CacheEntrySource(Enum):
    ENV = "ENV"
    SECRETSMANAGER = "SECRETSMANAGER"
    DEFAULT = "DEFAULT"


class CacheEntryType(Enum):
    STRING = str
    INTEGER = int
    FLOAT = float
    BOOLEAN = bool


class CacheEntry:
    def __init__(
        self,
        key: str,
        source: CacheEntrySource,
        type: CacheEntryType,
        value: any,
        required: bool = False,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        self.key = key
        self.source = source
        self.type = type
        self.value = value
        self.required = required
        self.change_callback_fn = change_callback_fn


class Cache:
    def __init__(self) -> None:
        self.cache = {}

    def set(self, cache_entry: CacheEntry) -> None:
        self.cache[cache_entry.key] = cache_entry

    def get(self, key: str) -> CacheEntry:
        return self.cache[key]
