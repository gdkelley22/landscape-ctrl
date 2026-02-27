"""
Unit tests for the base HTTP client (api/client.py).

Uses respx to intercept httpx calls — no real network traffic.
"""

import pytest
import respx
import httpx

from landscape_ctrl.api.client import LandscapeClient, LandscapeAPIError, AuthError
from landscape_ctrl.config import LandscapeConfig


BASE = "https://landscape.example.com"


def make_cfg(**kwargs) -> LandscapeConfig:
    defaults = dict(
        url=BASE,
        account="standalone",
        api_version="v2",
        access_key="TESTKEY",
        verify_ssl=False,
    )
    defaults.update(kwargs)
    return LandscapeConfig(**defaults)


@pytest.mark.asyncio
class TestGetJson:
    @respx.mock
    async def test_success(self):
        respx.get(f"{BASE}/api/v2/computers").mock(
            return_value=httpx.Response(200, json={"results": [], "count": 0})
        )
        async with LandscapeClient(make_cfg()) as client:
            client._token = "faketoken"
            data = await client.get_json("/computers")
        assert data["count"] == 0

    @respx.mock
    async def test_raises_on_404(self):
        respx.get(f"{BASE}/api/v2/computers/9999").mock(
            return_value=httpx.Response(404, json={"message": "not found"})
        )
        async with LandscapeClient(make_cfg()) as client:
            client._token = "faketoken"
            with pytest.raises(LandscapeAPIError) as exc_info:
                await client.get_json("/computers/9999")
        assert exc_info.value.status_code == 404

    @respx.mock
    async def test_raises_auth_error_on_401(self, monkeypatch):
        # Suppress retry attempt by monkeypatching get_secret_key to return None
        monkeypatch.setattr("landscape_ctrl.api.client.get_secret_key", lambda: None)
        respx.get(f"{BASE}/api/v2/computers").mock(
            return_value=httpx.Response(401, json={"message": "unauthorized"})
        )
        async with LandscapeClient(make_cfg()) as client:
            client._token = "expiredtoken"
            with pytest.raises(AuthError):
                await client.get_json("/computers")


@pytest.mark.asyncio
class TestLoginWithAccessKey:
    @respx.mock
    async def test_stores_token(self, tmp_path, monkeypatch):
        monkeypatch.setattr("landscape_ctrl.api.client.save_token", lambda t: None)
        respx.post(f"{BASE}/api/v2/login/access-key").mock(
            return_value=httpx.Response(200, json={"token": "jwt.abc.xyz"})
        )
        async with LandscapeClient(make_cfg()) as client:
            token = await client.login_with_access_key("KEY", "SECRET")
        assert token == "jwt.abc.xyz"
        assert client._token == "jwt.abc.xyz"


@pytest.mark.asyncio
class TestPaginate:
    async def test_follows_next(self):
        page2_url = f"{BASE}/api/v2/computers?offset=2"

        call_count = 0

        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json={
                    "results": [{"id": 1, "hostname": "a"}, {"id": 2, "hostname": "b"}],
                    "next": page2_url,
                    "count": 4,
                })
            else:
                return httpx.Response(200, json={
                    "results": [{"id": 3, "hostname": "c"}, {"id": 4, "hostname": "d"}],
                    "next": None,
                    "count": 4,
                })

        with respx.mock:
            respx.route(method="GET", host="landscape.example.com").mock(side_effect=side_effect)

            async with LandscapeClient(make_cfg()) as client:
                client._token = "faketoken"
                items = [item async for item in client.paginate("/computers")]

        assert len(items) == 4
        assert items[0]["hostname"] == "a"
        assert items[3]["hostname"] == "d"
        assert call_count == 2
