from __future__ import annotations

import os

import uvicorn


def _get_host() -> str:
    return os.getenv("HOST", "0.0.0.0")


def _get_port() -> int:
    try:
        return int(os.getenv("PORT", "8000"))
    except ValueError:
        return 8000


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=_get_host(),
        port=_get_port(),
        reload=os.getenv("RELOAD", "0") == "1",
    )
