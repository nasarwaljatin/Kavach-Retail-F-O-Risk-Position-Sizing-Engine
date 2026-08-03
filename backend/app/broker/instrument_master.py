"""
Instrument token resolution for Angel One SmartAPI.

Angel One requires a numeric `symboltoken` for both ltpData() and placeOrder().
The full instrument list is published daily at:
  https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json

Each entry example:
  {"token": "26009", "symbol": "NIFTY28OCT2524400CE", "name": "NIFTY",
   "expiry": "28OCT2025", "strike": "2440000.000000", "lotsize": "75",
   "instrumenttype": "OPTIDX", "exch_seg": "NFO", "tick_size": "5.000000"}

Note: `strike` is actual strike price x100 (2440000 = strike 24400).

Caching strategy: download once daily to a local JSON file.
File is ~25 MB — do NOT refresh on every request.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx

logger = logging.getLogger("kavach.broker.instrument_master")

# URL order: primary -> fallback mirror
_CDN_URLS = [
    "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json",
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
]

# Cache file lives under backend/data/  (volume-mounted in Docker, gitignored)
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_CACHE_FILE = _CACHE_DIR / "instrument_master.json"

# Refresh once every 24 hours
_TTL_SECONDS = 86_400


class InstrumentMaster:
    """
    Singleton that holds the in-memory token lookup table.

    Usage:
        master = InstrumentMaster.get()
        token = master.resolve_token("NIFTY28OCT2524400CE", "NFO")
    """

    _instance: Optional["InstrumentMaster"] = None

    def __init__(self) -> None:
        # Dict keyed by (exchange, tradingsymbol) -> token str
        self._index: Dict[Tuple[str, str], str] = {}
        self._loaded = False

    @classmethod
    def get(cls) -> "InstrumentMaster":
        """Return the singleton, loading data if needed."""
        if cls._instance is None:
            cls._instance = cls()
        if not cls._instance._loaded:
            cls._instance._load()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Force a fresh load on next access. Used in tests."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_token(self, tradingsymbol: str, exchange: str) -> str:
        """
        Return the numeric token string for (tradingsymbol, exchange).

        Returns "" if not found — callers must handle this gracefully.
        Never raises an exception.
        """
        if not self._loaded:
            self._load()
        key = (exchange.upper(), tradingsymbol.upper())
        token = self._index.get(key, "")
        if not token:
            logger.warning(
                "Token not found for symbol=%s exchange=%s. "
                "Ensure instrument master is up-to-date.",
                tradingsymbol,
                exchange,
            )
        return token

    # ------------------------------------------------------------------
    # Internal loading & caching
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load token data from cache or network, build index."""
        try:
            raw = self._read_or_refresh_cache()
            self._build_index(raw)
            self._loaded = True
            logger.info(
                "Instrument master loaded: %d symbols indexed.", len(self._index)
            )
        except Exception as exc:
            # Non-fatal: system runs without token resolution
            logger.error(
                "Failed to load instrument master: %s. "
                "Token resolution will return empty strings.",
                exc,
            )
            self._loaded = True  # Prevent repeated failing attempts in same process

    def _read_or_refresh_cache(self) -> list:
        """Return parsed JSON list, refreshing cache if stale."""
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

        cache_age = self._cache_age_seconds()
        if cache_age is not None and cache_age < _TTL_SECONDS:
            logger.debug(
                "Using cached instrument master (age=%.0fs < TTL=%ds).",
                cache_age,
                _TTL_SECONDS,
            )
            with open(_CACHE_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)

        logger.info("Instrument master cache is stale or missing -- downloading...")
        raw = self._download()
        # Persist to cache
        with open(_CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(raw, fh)
        logger.info(
            "Instrument master cached to %s (%d entries).", _CACHE_FILE, len(raw)
        )
        return raw

    @staticmethod
    def _cache_age_seconds() -> Optional[float]:
        """Return seconds since last cache write, or None if file absent."""
        if not _CACHE_FILE.exists():
            return None
        return time.time() - _CACHE_FILE.stat().st_mtime

    @staticmethod
    def _download() -> list:
        """Download from CDN with fallback mirror. Returns parsed list."""
        last_exc: Exception = RuntimeError("No CDN URLs configured.")
        for url in _CDN_URLS:
            try:
                logger.debug("Downloading instrument master from %s", url)
                resp = httpx.get(url, timeout=30.0, follow_redirects=True)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)
                last_exc = exc
        raise last_exc

    def _build_index(self, records: list) -> None:
        """Build (exchange, symbol) -> token dict from raw records."""
        self._index.clear()
        for rec in records:
            token = str(rec.get("token", "")).strip()
            symbol = str(rec.get("symbol", "")).strip().upper()
            exchange = str(rec.get("exch_seg", "")).strip().upper()
            if token and symbol and exchange:
                self._index[(exchange, symbol)] = token
        logger.debug("Index built: %d entries.", len(self._index))

    def load_from_records(self, records: list) -> None:
        """
        Directly load from a list of dicts (used in tests to bypass file I/O).
        """
        self._build_index(records)
        self._loaded = True


# Module-level convenience function
def resolve_token(tradingsymbol: str, exchange: str) -> str:
    """Resolve Angel One symboltoken for (tradingsymbol, exchange)."""
    return InstrumentMaster.get().resolve_token(tradingsymbol, exchange)
