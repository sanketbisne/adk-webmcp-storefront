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

"""ADK FunctionTools bridging to browser-native WebMCP tools."""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from app.webmcp_bridge import bridge_manager, dispatch_webmcp_tool
from app.webmcp_store import store


def _resolve_session_id(tool_context: ToolContext) -> str:
    session = getattr(tool_context, "session", None)
    return (
        str(tool_context.state.get("webmcp_session_id", ""))
        or str(getattr(session, "id", "") or "")
        or "default"
    )


async def list_webmcp_tools(tool_context: ToolContext) -> dict[str, Any]:
    """Discover all WebMCP tools exposed by the active browser page via navigator.modelContext.

    Returns:
        Dictionary containing connection status, imperative tools registered via
        navigator.modelContext.registerTool, and declarative HTML form tools.
    """
    del tool_context
    tools = store.get_registered_tools()
    return {
        "status": "success",
        "connected_browser_tabs": bridge_manager.connected_tabs,
        "tool_count": len(tools),
        "tools": [
            {
                "name": t["name"],
                "source": t.get("source", "imperative"),
                "api": t.get("api", "navigator.modelContext.registerTool"),
                "description": t["description"],
                "parameters": list(
                    (t.get("inputSchema") or {}).get("properties", {}).keys()
                ),
            }
            for t in tools
        ],
    }


async def search_products(
    query: str,
    category: str,
    max_price: float,
    in_stock_only: bool,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Search and filter the NexusGear storefront catalog via WebMCP.

    Args:
        query: Keyword search term (pass "" to match all keywords).
        category: Category name: "audio", "peripherals", "travel", "monitors", or "" for all.
        max_price: Maximum unit price in USD (pass 0 to apply no price cap).
        in_stock_only: True to exclude out-of-stock products, False to include all.

    Returns:
        Dictionary with matching products, prices, ratings, stock counts, and applied filters.
    """
    session_id = _resolve_session_id(tool_context)
    return await dispatch_webmcp_tool(
        "search_products",
        {
            "query": query,
            "category": category,
            "max_price": max_price,
            "in_stock_only": in_stock_only,
        },
        session_id=session_id,
    )


async def get_product_details(
    product_id: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Retrieve complete technical specs, stock count, and description for a product.

    Args:
        product_id: Exact product identifier from the catalog (for example "prod-101").

    Returns:
        Dictionary containing full product metadata and technical specifications.
    """
    session_id = _resolve_session_id(tool_context)
    return await dispatch_webmcp_tool(
        "get_product_details",
        {"product_id": product_id},
        session_id=session_id,
    )


async def add_to_cart(
    product_id: str,
    quantity: int,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Add an in-stock product to the browser's active shopping cart via WebMCP.

    Args:
        product_id: Product identifier (for example "prod-101").
        quantity: Number of units to add (integer from 1 to 10).

    Returns:
        Dictionary with the added item details and updated shopping cart summary.
    """
    session_id = _resolve_session_id(tool_context)
    return await dispatch_webmcp_tool(
        "add_to_cart",
        {"product_id": product_id, "quantity": quantity},
        session_id=session_id,
    )


async def remove_from_cart(
    product_id: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Remove a product from the active shopping cart via WebMCP.

    Args:
        product_id: Product identifier to remove (for example "prod-101").

    Returns:
        Dictionary with updated shopping cart summary.
    """
    session_id = _resolve_session_id(tool_context)
    return await dispatch_webmcp_tool(
        "remove_from_cart",
        {"product_id": product_id},
        session_id=session_id,
    )


async def get_cart(tool_context: ToolContext) -> dict[str, Any]:
    """Inspect the active shopping cart items, discounts, shipping fee, and total.

    Returns:
        Dictionary with line items, subtotal, applied promo code, discount, and total.
    """
    session_id = _resolve_session_id(tool_context)
    return await dispatch_webmcp_tool("get_cart", {}, session_id=session_id)


async def apply_promo_code(
    code: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Apply a promotional discount code to the active shopping cart via WebMCP.

    Args:
        code: Promotional code string (such as "WEBMCP20", "ADK10", or "SAVE25").

    Returns:
        Dictionary with discount details and recalculated cart totals.
    """
    session_id = _resolve_session_id(tool_context)
    return await dispatch_webmcp_tool(
        "apply_promo_code",
        {"code": code},
        session_id=session_id,
    )


async def update_shipping_form(
    full_name: str,
    email: str,
    address: str,
    delivery_speed: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Populate the storefront's Declarative WebMCP HTML shipping form (<form toolname="update_shipping_form">).

    Args:
        full_name: Recipient full name.
        email: Recipient email address.
        address: Complete street, city, state, and postal address.
        delivery_speed: One of "standard" ($0), "express" ($15), or "overnight" ($29).

    Returns:
        Dictionary confirming form population and updated shipping fee in cart summary.
    """
    session_id = _resolve_session_id(tool_context)
    return await dispatch_webmcp_tool(
        "update_shipping_form",
        {
            "full_name": full_name,
            "email": email,
            "address": address,
            "delivery_speed": delivery_speed,
        },
        session_id=session_id,
    )


async def checkout_order(
    full_name: str,
    address: str,
    user_confirmed: bool,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Finalize purchase for the current shopping cart via WebMCP.

    IMPORTANT: This action is irreversible. Only pass user_confirmed=True when the
    user has explicitly confirmed placing the order (e.g. "Yes, I confirm").

    Args:
        full_name: Recipient full name for the order.
        address: Complete shipping destination address.
        user_confirmed: True ONLY when the user's message explicitly confirms placing the order; otherwise False.

    Returns:
        Dictionary containing the confirmed order receipt and order_id, or a confirmation prompt if blocked.
    """
    session_id = _resolve_session_id(tool_context)
    return await dispatch_webmcp_tool(
        "checkout_order",
        {
            "full_name": full_name,
            "address": address,
            "user_confirmed": user_confirmed,
        },
        session_id=session_id,
    )
