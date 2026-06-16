import socket
from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine = None
_SessionLocal = None


def _resolve_ipv4_connect_args(database_url: str) -> dict:
    """IPv6 非対応環境 (GitHub Actions 等) のために IPv4 アドレスを明示する。
    psycopg2 の hostaddr パラメータは SSL ホスト名検証に hostname を使いつつ
    接続先 IP だけを上書きできる。"""
    try:
        hostname = urlparse(database_url).hostname
        if hostname is None:
            return {}
        ipv4 = socket.getaddrinfo(hostname, None, socket.AF_INET)[0][4][0]
        return {"hostaddr": ipv4}
    except (socket.gaierror, IndexError):
        return {}


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        from src.config import get_settings
        settings = get_settings()
        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args=_resolve_ipv4_connect_args(settings.DATABASE_URL),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False)
    return _engine


@property
def engine():
    return _get_engine()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    _get_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
