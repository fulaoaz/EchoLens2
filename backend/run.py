"""EchoLens 2.0 backend launcher.

Boots the Flask app on 0.0.0.0:5001 with threaded request handling.
On Windows, forces UTF-8 for stdio so logs render correctly.
"""

from __future__ import annotations

import os
import sys

from app import create_app
from app.config import get_settings


def _force_utf8_on_windows() -> None:
    if sys.platform.startswith("win"):
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            except (AttributeError, ValueError):
                pass
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def main() -> None:
    _force_utf8_on_windows()
    settings = get_settings()
    app = create_app()
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(
        host="0.0.0.0",
        port=5001,
        threaded=True,
        debug=debug,
        use_reloader=False,
    )
    _ = settings  # keep settings referenced for early validation


if __name__ == "__main__":
    main()
