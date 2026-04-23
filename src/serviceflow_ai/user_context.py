"""Thread-local user session — tells tools which business's documents to load."""
import threading

_ctx = threading.local()


def set_active_user(user_id: int) -> None:
    _ctx.user_id = user_id


def get_active_user() -> int | None:
    return getattr(_ctx, "user_id", None)


def clear_active_user() -> None:
    _ctx.user_id = None
