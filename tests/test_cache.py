"""Tests for hookrunner.cache."""

import json
import os
import time

import pytest

from hookrunner.cache import (
    CacheError,
    _cache_path,
    clear_cache,
    get_cached,
    invalidate,
    set_cached,
)

URL = "https://example.com/hooks.yml"
CONTENT = "pre-commit:\n  - echo hello"


@pytest.fixture()
def cache_dir(tmp_path):
    return str(tmp_path / "cache")


def test_set_and_get_cached(cache_dir):
    set_cached(URL, CONTENT, cache_dir=cache_dir)
    result = get_cached(URL, ttl=60, cache_dir=cache_dir)
    assert result == CONTENT


def test_get_cached_returns_none_when_missing(cache_dir):
    result = get_cached(URL, ttl=60, cache_dir=cache_dir)
    assert result is None


def test_get_cached_returns_none_when_expired(cache_dir):
    set_cached(URL, CONTENT, cache_dir=cache_dir)
    path = _cache_path(URL, cache_dir)
    # Backdate the timestamp so the entry appears expired.
    with open(path, "r", encoding="utf-8") as fh:
        entry = json.load(fh)
    entry["timestamp"] = time.time() - 9999
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entry, fh)
    result = get_cached(URL, ttl=60, cache_dir=cache_dir)
    assert result is None


def test_get_cached_raises_on_corrupt_file(cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    path = _cache_path(URL, cache_dir)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("not valid json{{{")
    with pytest.raises(CacheError):
        get_cached(URL, ttl=60, cache_dir=cache_dir)


def test_invalidate_removes_entry(cache_dir):
    set_cached(URL, CONTENT, cache_dir=cache_dir)
    removed = invalidate(URL, cache_dir=cache_dir)
    assert removed is True
    assert get_cached(URL, ttl=60, cache_dir=cache_dir) is None


def test_invalidate_returns_false_when_not_present(cache_dir):
    assert invalidate(URL, cache_dir=cache_dir) is False


def test_clear_cache_removes_all_entries(cache_dir):
    set_cached(URL, CONTENT, cache_dir=cache_dir)
    set_cached(URL + "/other", CONTENT, cache_dir=cache_dir)
    count = clear_cache(cache_dir=cache_dir)
    assert count == 2
    assert get_cached(URL, ttl=60, cache_dir=cache_dir) is None


def test_clear_cache_returns_zero_when_dir_missing(tmp_path):
    missing = str(tmp_path / "nonexistent")
    assert clear_cache(cache_dir=missing) == 0


def test_set_cached_creates_cache_dir(tmp_path):
    cache_dir = str(tmp_path / "deep" / "cache")
    set_cached(URL, CONTENT, cache_dir=cache_dir)
    assert os.path.isdir(cache_dir)
