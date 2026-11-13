# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Deterministic unit tests for WebMCP store, guardrails, bridge, and ADK wiring."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from app.agent import app as adk_app
from app.agent import root_agent
from app.bridge_server import bridge_app
from app.guardrails import (
    checkout_confirmation_guard,
    has_explicit_confirmation,
    input_validation_guard,
)
from app.webmcp_bridge import WebMcpBridgeManager
from app.webmcp_store import WebMcpStore, store


def _fake_tool(name: str) -> Any:
    return SimpleNamespace(name=name)


def _fake_tool_context(user_text: str, session_id: str = "unit-session") -> Any:
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_text)],
    )
    return SimpleNamespace(
        user_content=content,
        session=SimpleNamespace(id=session_id),
        state={"webmcp_session_id": session_id, "latest_user_message": user_text},
    )


def test_agent_and_app_wiring() -> None:
    """Verify ADK root_agent and App preserve required naming and tool bindings."""
    assert root_agent.name == "webmcp_agent"
    assert adk_app.name == "app"
    tool_names = {
        getattr(t, "__name__", getattr(t, "name", "")) for t in root_agent.tools
    }
    expected = {
        "list_webmcp_tools",
        "search_products",
        "get_product_details",
        "add_to_cart",
        "remove_from_cart",
        "get_cart",
        "apply_promo_code",
        "update_shipping_form",
        "checkout_order",
    }
    assert expected.issubset(tool_names)


def test_webmcp_store_search_and_filters() -> None:
    """Verify catalog search, max_price cap, and in_stock_only filters."""
    local_store = WebMcpStore()

    anc_under_300 = local_store.search_products(
        query="ANC",
        category="audio",
        max_price=300.0,
        in_stock_only=True,
    )
    assert anc_under_300["status"] == "success"
    returned_ids = {p["product_id"] for p in anc_under_300["products"]}
    assert returned_ids == {"prod-101", "prod-102"}
    assert "prod-103" not in returned_ids  # $399 exceeds $300

    travel_all = local_store.search_products(category="travel", in_stock_only=False)
    assert travel_all["count"] == 2

    travel_in_stock = local_store.search_products(category="travel", in_stock_only=True)
    assert travel_in_stock["count"] == 1
    assert travel_in_stock["products"][0]["product_id"] == "prod-107"


def test_webmcp_store_cart_promo_declarative_form_and_checkout() -> None:
    """Verify full shopping lifecycle: add_to_cart, promo math, shipping, checkout."""
    local_store = WebMcpStore()

    # Out of stock product should be rejected cleanly
    oos = local_store.add_to_cart("prod-106", quantity=1, session_id="s1")
    assert oos["status"] == "error"

    # Add AeroPulse Pro ($249.00)
    added = local_store.add_to_cart("prod-101", quantity=1, session_id="s1")
    assert added["status"] == "success"
    assert added["cart"]["subtotal"] == 249.00

    # Apply WEBMCP20 (20% off -> $49.80 discount -> $199.20)
    promo = local_store.apply_promo_code("WEBMCP20", session_id="s1")
    assert promo["status"] == "success"
    assert promo["cart"]["discount"] == 49.80
    assert promo["cart"]["total"] == 199.20

    # Declarative HTML form update with express delivery (+$15.00 -> $214.20)
    ship = local_store.update_shipping_form(
        full_name="Alex Rivera",
        email="alex@example.com",
        address="123 Market St, San Francisco, CA",
        delivery_speed="express",
        session_id="s1",
    )
    assert ship["status"] == "success"
    assert ship["webmcp_source"] == "declarative_form"
    assert ship["cart"]["shipping_fee"] == 15.00
    assert ship["cart"]["total"] == 214.20

    # Complete checkout
    order = local_store.checkout_order(
        full_name="Alex Rivera",
        address="123 Market St, San Francisco, CA",
        session_id="s1",
    )
    assert order["status"] == "success"
    assert order["order"]["order_id"].startswith("NXG-")
    assert order["order"]["total_charged"] == 214.20

    # Cart cleared & stock decremented (14 -> 13)
    after_cart = local_store.get_cart(session_id="s1")
    assert after_cart["cart"]["item_count"] == 0
    details = local_store.get_product_details("prod-101")
    assert details["product"]["stock"] == 13


@pytest.mark.asyncio
async def test_input_validation_guard() -> None:
    """Verify script-injection payloads and out-of-range quantities are blocked."""
    ctx = _fake_tool_context("Add item")

    blocked_xss = await input_validation_guard(
        _fake_tool("update_shipping_form"),
        {
            "full_name": "<script>alert(1)</script>",
            "email": "a@b.com",
            "address": "1 Main",
            "delivery_speed": "standard",
        },
        ctx,
    )
    assert blocked_xss is not None
    assert blocked_xss["status"] == "blocked"

    blocked_qty_zero = await input_validation_guard(
        _fake_tool("add_to_cart"),
        {"product_id": "prod-101", "quantity": 0},
        ctx,
    )
    assert blocked_qty_zero is not None
    assert blocked_qty_zero["status"] == "blocked"

    blocked_qty_high = await input_validation_guard(
        _fake_tool("add_to_cart"),
        {"product_id": "prod-101", "quantity": 25},
        ctx,
    )
    assert blocked_qty_high is not None
    assert blocked_qty_high["status"] == "blocked"

    allowed = await input_validation_guard(
        _fake_tool("add_to_cart"),
        {"product_id": "prod-101", "quantity": 2},
        ctx,
    )
    assert allowed is None


@pytest.mark.asyncio
async def test_checkout_confirmation_guard() -> None:
    """Verify checkout_order is deterministically blocked without user confirmation."""
    store.reset()
    store.add_to_cart("prod-104", quantity=1, session_id="guard-sess")

    # 1. Unconfirmed immediate checkout prompt — blocked even if LLM sets user_confirmed=True
    unconfirmed_ctx = _fake_tool_context(
        "Add the keyboard and check out immediately to 123 Main St.",
        session_id="guard-sess",
    )
    res_sneaky = await checkout_confirmation_guard(
        _fake_tool("checkout_order"),
        {"full_name": "Alex", "address": "123 Main St", "user_confirmed": True},
        unconfirmed_ctx,
    )
    assert res_sneaky is not None
    assert res_sneaky["status"] == "confirmation_required"

    # 2. Negated confirmation — blocked
    assert not has_explicit_confirmation("No, do not confirm this order.")

    # 3. Explicit confirmation + user_confirmed=True — allowed (returns None)
    confirmed_ctx = _fake_tool_context(
        "Yes, I confirm! Please place the order to 123 Main St.",
        session_id="guard-sess",
    )
    res_allowed = await checkout_confirmation_guard(
        _fake_tool("checkout_order"),
        {"full_name": "Alex", "address": "123 Main St", "user_confirmed": True},
        confirmed_ctx,
    )
    assert res_allowed is None


@pytest.mark.asyncio
async def test_webmcp_bridge_http_and_websocket_relay() -> None:
    """Verify REST endpoints, static WebMCP SDK assets, and live WS tool relay."""
    store.reset()
    client = TestClient(bridge_app)

    # Storefront & SDK asset served cleanly
    html_resp = client.get("/webmcp")
    assert html_resp.status_code == 200
    assert 'toolname="update_shipping_form"' in html_resp.text

    sdk_resp = client.get("/webmcp-assets/webmcp-sdk.js")
    assert sdk_resp.status_code == 200
    assert "modelContext" in sdk_resp.text

    status_resp = client.get("/api/webmcp/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["registered_tool_count"] == 8

    # Verify WebSocket init handshake over FastAPI route
    with client.websocket_connect("/ws/webmcp") as ws:
        init_msg = ws.receive_json()
        assert init_msg["type"] == "webmcp:init"

    # Verify live async bi-directional WebMCP RPC relay (agent -> browser WS -> agent)
    manager = WebMcpBridgeManager()
    outbound: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    class _FakeBrowserWebSocket:
        async def accept(self) -> None:
            return None

        async def send_json(self, payload: dict[str, Any]) -> None:
            await outbound.put(payload)

    fake_ws = _FakeBrowserWebSocket()
    await manager.connect("tab-test", fake_ws)  # type: ignore[arg-type]
    first_frame = await outbound.get()
    assert first_frame["type"] == "webmcp:init"

    async def _simulate_browser_tab() -> None:
        rpc_msg = await outbound.get()
        assert rpc_msg["type"] == "webmcp:call_tool"
        assert rpc_msg["tool"] == "add_to_cart"
        await manager.handle_message(
            "tab-test",
            {
                "type": "webmcp:tool_result",
                "callId": rpc_msg["callId"],
                "result": rpc_msg["canonicalResult"],
            },
        )

    browser_task = asyncio.create_task(_simulate_browser_tab())
    result = await manager.execute_tool(
        "add_to_cart", {"product_id": "prod-101", "quantity": 1}
    )
    await browser_task

    assert result["status"] == "success"
    assert result["webmcp_transport"] == "live_browser_ws"
    assert result["cart"]["total"] == 249.00
