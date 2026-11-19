"""A interface servida pelo backend: index.html sempre revalidado, assets com hash em cache."""

import pytest
from fastapi.testclient import TestClient

from app.api import main


@pytest.mark.skipif(not main.FRONTEND_DIST.exists(), reason="frontend/dist não compilado")
def test_index_is_revalidated_and_hashed_assets_are_not():
    client = TestClient(main.app)
    assert client.get("/").headers.get("cache-control") == "no-cache"
    asset = next((main.FRONTEND_DIST / "assets").glob("*.js")).name
    assert client.get(f"/assets/{asset}").headers.get("cache-control") is None
