"""Shared path resolver for business document tools — respects the active user context."""
from pathlib import Path

from serviceflow_ai.user_context import get_active_user


def get_business_file_path(filename: str) -> Path:
    project_root = Path(__file__).resolve().parents[4]
    uid = get_active_user()
    if uid is not None:
        return project_root / "data" / "uploads" / "users" / str(uid) / filename
    return project_root / "data" / "uploads" / "current_business" / filename
