"""Parquet cache helpers — avoid re-hitting BPIPE on every backtest run."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from config import CACHE_DIR


def _key_to_path(key: str) -> Path:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:16]
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:80]
    return CACHE_DIR / f"{safe}__{digest}.parquet"


def cache_path(key: str) -> Path:
    return _key_to_path(key)


def read_cache(key: str) -> pd.DataFrame | None:
    path = _key_to_path(key)
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        if "date" in df.columns:
            df = df.set_index("date")
        df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df.sort_index()


def write_cache(key: str, df: pd.DataFrame) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _key_to_path(key)
    out = df.copy()
    if out.index.name != "date":
        out.index.name = "date"
    out.to_parquet(path)
    return path


def cached_frame(
    key: str,
    builder,
    *,
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    """Return cached parquet if present, else call builder() and persist."""
    if use_cache and not refresh:
        hit = read_cache(key)
        if hit is not None and not hit.empty:
            return hit
    df = builder()
    if use_cache and df is not None and not df.empty:
        write_cache(key, df)
    return df
