"""Simple file-based cache for remote hook configs to avoid redundant fetches."""

import hashlib
import json
import os
import time
from typing import Optional

DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".hookrunner", "cache")
DEFAULT_TTL = 300  # seconds


class CacheError(Exception):
    """Raised when a cache operation fails."""


def _cache_key(url: str) -> str:
    """Return a filesystem-safe cache key derived from the URL."""
    return hashlib.sha256(url.encode()).hexdigest()


def _cache_path(url: str, cache_dir: str = DEFAULT_CACHE_DIR) -> str:
    return os.path.join(cache_dir, _cache_key(url) + ".json")


def get_cached(url: str, ttl: int = DEFAULT_TTL, cache_dir: str = DEFAULT_CACHE_DIR) -> Optional[str]:
    """Return cached content for *url* if it exists and has not expired.

    Returns ``None`` when the entry is missing or stale.
    """
    path = _cache_path(url, cache_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            entry = json.load(fh)
        if time.time() - entry["timestamp"] > ttl:
            return None
        return entry["content"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise CacheError(f"Failed to read cache entry for {url!r}: {exc}") from exc


def set_cached(url: str, content: str, cache_dir: str = DEFAULT_CACHE_DIR) -> None:
    """Persist *content* for *url* in the cache directory."""
    os.makedirs(cache_dir, exist_ok=True)
    path = _cache_path(url, cache_dir)
    entry = {"url": url, "timestamp": time.time(), "content": content}
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(entry, fh)
    except OSError as exc:
        raise CacheError(f"Failed to write cache entry for {url!r}: {exc}") from exc


def invalidate(url: str, cache_dir: str = DEFAULT_CACHE_DIR) -> bool:
    """Remove the cached entry for *url*.  Returns ``True`` if an entry was removed."""
    path = _cache_path(url, cache_dir)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def clear_cache(cache_dir: str = DEFAULT_CACHE_DIR) -> int:
    """Delete all cache entries.  Returns the number of files removed."""
    if not os.path.isdir(cache_dir):
        return 0
    removed = 0
    for name in os.listdir(cache_dir):
        if name.endswith(".json"):
            os.remove(os.path.join(cache_dir, name))
            removed += 1
    return removed
