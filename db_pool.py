"""PostgreSQL connection pool with automatic failover between two hosts.

This module can read database configuration either from environment variables
or from a Django ``settings`` object passed via :func:`init_db`.
"""

import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

import psycopg2
from psycopg2 import pool

_pool_tigo: Optional[pool.ThreadedConnectionPool] = None
_pool_claro: Optional[pool.ThreadedConnectionPool] = None
_active_pool: Optional[pool.ThreadedConnectionPool] = None

_is_using_tigo = False
_reconnecting = False
_connection_initialized = False

_health_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_last_tigo_check = 0.0
_failed_tigo_attempts = 0

# Optional Django settings module. When provided via :func:`init_db`,
# configuration values will be read from here instead of the environment.
_settings = None


def init_db(settings_module: Optional[Any] = None) -> None:
    """Initialize the module with a Django ``settings`` object.

    Parameters
    ----------
    settings_module:
        A module or object from which configuration attributes can be read.
        If ``None``, the module will fall back to environment variables.
    """

    global _settings
    _settings = settings_module

HEALTH_CHECK_INTERVAL = 30
TIGO_RECONNECT_INTERVAL = 2 * 60
MAX_FAILED_ATTEMPTS = 3
MAX_RECONNECT_INTERVAL = 10 * 60


def _base_config() -> Dict[str, Any]:
    def _get(name: str, default: Optional[str] = None) -> Optional[str]:
        if _settings and hasattr(_settings, name):
            return getattr(_settings, name)
        return os.getenv(name, default)

    return {
        "user": _get("DB_USER"),
        "password": _get("DB_PASSWORD"),
        "port": int(_get("DB_PORT", "5432")),
        "dbname": _get("DB_NAME"),
        "connect_timeout": 15,
        "options": "-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000",
    }


def _config_tigo() -> Dict[str, Any]:
    cfg = _base_config()
    def _get(name: str) -> Optional[str]:
        if _settings and hasattr(_settings, name):
            return getattr(_settings, name)
        return os.getenv(name)

    cfg["host"] = _get("DB_HOST_TIGO")
    cfg["minconn"] = 5
    cfg["maxconn"] = 25
    return cfg


def _config_claro() -> Dict[str, Any]:
    cfg = _base_config()
    def _get(name: str) -> Optional[str]:
        if _settings and hasattr(_settings, name):
            return getattr(_settings, name)
        return os.getenv(name)

    cfg["host"] = _get("DB_HOST_CLARO")
    cfg["minconn"] = 5
    cfg["maxconn"] = 20
    return cfg


def _create_pool(cfg: Dict[str, Any], name: str) -> Optional[pool.ThreadedConnectionPool]:
    minconn = int(cfg.pop("minconn", 5))
    maxconn = int(cfg.pop("maxconn", 25))
    try:
        p = pool.ThreadedConnectionPool(minconn, maxconn, **cfg)
        conn = p.getconn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        p.putconn(conn)
        print(f"Pool {name} created")
        return p
    except Exception as exc:
        print(f"Error creating pool {name}: {exc}")
        return None


def _check_pool_health(p: pool.ThreadedConnectionPool, name: str) -> bool:
    try:
        conn = p.getconn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        p.putconn(conn)
        return True
    except Exception as exc:
        print(f"Health check failed for {name}: {exc}")
        return False


def _try_connect_tigo() -> bool:
    global _pool_tigo, _failed_tigo_attempts
    if _pool_tigo and _check_pool_health(_pool_tigo, "TIGO"):
        print("Existing TIGO pool is healthy")
        return True
    if _pool_tigo:
        try:
            _pool_tigo.closeall()
        except Exception:
            pass
        _pool_tigo = None
    cfg = _config_tigo()
    _pool_tigo = _create_pool(cfg, "TIGO")
    if _pool_tigo:
        _failed_tigo_attempts = 0
        return True
    _failed_tigo_attempts += 1
    return False


def _connect_claro() -> pool.ThreadedConnectionPool:
    global _pool_claro
    if _pool_claro and _check_pool_health(_pool_claro, "CLARO"):
        print("Existing CLARO pool is healthy")
        return _pool_claro
    if _pool_claro:
        try:
            _pool_claro.closeall()
        except Exception:
            pass
        _pool_claro = None
    cfg = _config_claro()
    p = _create_pool(cfg, "CLARO")
    if not p:
        raise RuntimeError("Failed to create CLARO pool")
    _pool_claro = p
    return p


def _switch_to_working_pool() -> Optional[pool.ThreadedConnectionPool]:
    global _active_pool, _is_using_tigo, _reconnecting
    if _reconnecting:
        return _active_pool
    _reconnecting = True
    try:
        if _try_connect_tigo() and _pool_tigo:
            if not _is_using_tigo or _active_pool != _pool_tigo:
                old = _active_pool
                _active_pool = _pool_tigo
                _is_using_tigo = True
                if old and old != _pool_tigo:
                    try:
                        old.closeall()
                    except Exception:
                        pass
            return _active_pool
        claro_pool = _connect_claro()
        old = _active_pool
        _active_pool = claro_pool
        _is_using_tigo = False
        if old and old != claro_pool:
            try:
                old.closeall()
            except Exception:
                pass
        return _active_pool
    finally:
        _reconnecting = False


def _health_loop():
    global _last_tigo_check
    while not _stop_event.wait(HEALTH_CHECK_INTERVAL):
        if _reconnecting:
            continue
        try:
            if not _is_using_tigo:
                now = time.time()
                interval = TIGO_RECONNECT_INTERVAL
                if _failed_tigo_attempts > MAX_FAILED_ATTEMPTS:
                    interval = min(
                        TIGO_RECONNECT_INTERVAL * 2 ** (_failed_tigo_attempts - MAX_FAILED_ATTEMPTS),
                        MAX_RECONNECT_INTERVAL,
                    )
                if now - _last_tigo_check >= interval:
                    _last_tigo_check = now
                    if _try_connect_tigo():
                        _switch_to_working_pool()
            if _active_pool and not _check_pool_health(_active_pool, "active"):
                _switch_to_working_pool()
        except Exception as exc:
            print(f"Health check error: {exc}")


def _setup_health_thread():
    global _health_thread
    if _health_thread and _health_thread.is_alive():
        return
    _health_thread = threading.Thread(target=_health_loop, daemon=True)
    _health_thread.start()


def initialize_pool() -> pool.ThreadedConnectionPool:
    global _connection_initialized, _active_pool
    if _connection_initialized and _active_pool:
        return _active_pool
    _active_pool = _switch_to_working_pool()
    if not _active_pool:
        raise RuntimeError("No pool available")
    _setup_health_thread()
    _connection_initialized = True
    return _active_pool


@contextmanager
def get_conn():
    if not _active_pool:
        initialize_pool()
    conn = _active_pool.getconn()
    try:
        yield conn
    finally:
        _active_pool.putconn(conn)


def execute_query(query: str, params: Optional[list] = None, retries: int = 0):
    MAX_RETRIES = 2
    if not _active_pool:
        initialize_pool()
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                return None
    except Exception as exc:
        print(f"Query error attempt {retries + 1}: {exc}")
        msg = str(exc).lower()
        if any(k in msg for k in ["connection", "timeout"]) and retries < MAX_RETRIES:
            _switch_to_working_pool()
            return execute_query(query, params, retries + 1)
        raise


def end_pools():
    _stop_event.set()
    if _health_thread:
        _health_thread.join(timeout=1)
    global _pool_tigo, _pool_claro, _active_pool, _connection_initialized, _is_using_tigo
    for p in (_pool_tigo, _pool_claro):
        if p:
            try:
                p.closeall()
            except Exception:
                pass
    _pool_tigo = None
    _pool_claro = None
    _active_pool = None
    _connection_initialized = False
    _is_using_tigo = False


def get_status() -> Dict[str, Any]:
    return {
        "is_connected": _active_pool is not None,
        "using_tigo": _is_using_tigo,
        "tigo_available": _pool_tigo is not None,
        "claro_available": _pool_claro is not None,
        "failed_tigo_attempts": _failed_tigo_attempts,
    }


class PoolWrapper:
    """Simple wrapper exposing a ``psycopg2`` pool-like API."""

    def query(self, query: str, params: Optional[list] = None):
        return execute_query(query, params)

    def connect(self):
        if not _active_pool:
            initialize_pool()
        return _active_pool.getconn()

    def end(self):
        end_pools()

    def get_status(self) -> Dict[str, Any]:
        return get_status()


pool = PoolWrapper()

query = execute_query
end = end_pools

