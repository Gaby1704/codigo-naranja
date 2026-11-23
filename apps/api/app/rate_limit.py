import time
from collections import defaultdict

from app.config import get_settings

_hits: dict[str, list[float]] = defaultdict(list)


def allow(key: str) -> bool:
    settings = get_settings()
    limit = max(1, settings.login_attempts)
    window = max(30, settings.login_window_seconds)
    now = time.monotonic()
    recent = [stamp for stamp in _hits[key] if now - stamp < window]
    if len(recent) >= limit:
        _hits[key] = recent
        return False
    recent.append(now)
    _hits[key] = recent
    return True


def reset() -> None:
    _hits.clear()
