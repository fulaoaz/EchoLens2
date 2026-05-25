"""Legacy stub-blueprint guard.

All registered API blueprints currently have implementation-specific tests. Add a
path here only when introducing a temporary 501 placeholder.
"""

from __future__ import annotations

from typing import Any

import pytest

# Stubs only — implemented blueprints leave this list and get their own tests.
STUB_PING_PATHS: list[str] = []


@pytest.mark.parametrize("path", STUB_PING_PATHS)
def test_stub_ping_returns_501(client: Any, path: str) -> None:
    resp = client.get(path)
    assert resp.status_code == 501, f"{path} returned {resp.status_code}"
    payload = resp.get_json()
    assert payload["implemented"] is False
    assert "todo" in payload
