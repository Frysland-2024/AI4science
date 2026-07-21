"""Materials Project credential lookup without logging secret values."""

from __future__ import annotations

import os


def configured_api_key() -> str | None:
    """Read a process key, then the Windows user-level environment."""
    key = os.environ.get("MP_API_KEY") or os.environ.get("PMG_MAPI_KEY")
    if key or os.name != "nt":
        return key
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
            for name in ("MP_API_KEY", "PMG_MAPI_KEY"):
                try:
                    value, _ = winreg.QueryValueEx(handle, name)
                except FileNotFoundError:
                    continue
                if value:
                    return str(value)
    except OSError:
        return None
    return None
