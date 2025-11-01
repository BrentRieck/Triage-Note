from app.db import _sync_url


def test_sync_url_leaves_plain_urls_unchanged():
    url = "postgresql://user:pass@host:5432/db"
    assert _sync_url(url) == url


def test_sync_url_strips_known_async_drivers():
    assert _sync_url("sqlite+aiosqlite:///./app.db") == "sqlite:///./app.db"
    assert (
        _sync_url("postgresql+asyncpg://user:pass@host:5432/db")
        == "postgresql://user:pass@host:5432/db"
    )


def test_sync_url_handles_unknown_async_drivers():
    assert (
        _sync_url("postgresql+propongo://user:pass@host:5432/db")
        == "postgresql://user:pass@host:5432/db"
    )
