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

"""Synchronized WebMCP storefront catalog, tool schemas, and session state."""

from __future__ import annotations

import copy
import datetime
import uuid
from typing import Any

CATALOG: list[dict[str, Any]] = [
    {
        "id": "prod-101",
        "name": "AeroPulse Pro ANC Headphones",
        "category": "audio",
        "price": 249.00,
        "rating": 4.9,
        "stock": 14,
        "badge": "Best Seller",
        "description": (
            "Flagship over-ear wireless noise-canceling headphones with adaptive 48dB "
            "ANC, 40-hour battery life, Bluetooth 5.4 multipoint, and USB-C lossless audio."
        ),
        "specs": {
            "anc": "Adaptive 48dB Hybrid ANC",
            "battery": "40 hours (ANC on)",
            "connectivity": "Bluetooth 5.4 + USB-C Audio",
            "weight": "254g",
        },
    },
    {
        "id": "prod-102",
        "name": "SonicBuds Lite Wireless Earbuds",
        "category": "audio",
        "price": 129.00,
        "rating": 4.6,
        "stock": 28,
        "badge": "Value Pick",
        "description": (
            "Compact true-wireless noise-canceling earbuds featuring 35dB hybrid ANC, "
            "IPX5 sweat resistance, spatial head-tracking, and 30-hour charging case."
        ),
        "specs": {
            "anc": "35dB Hybrid ANC",
            "battery": "8h buds / 30h case",
            "water_resistance": "IPX5",
            "weight": "4.8g per earbud",
        },
    },
    {
        "id": "prod-103",
        "name": "StudioMax Planar ANC Headphones",
        "category": "audio",
        "price": 399.00,
        "rating": 4.8,
        "stock": 6,
        "badge": "Audiophile",
        "description": (
            "Reference-grade planar magnetic wireless headphones with studio-tuned ANC "
            "and CNC magnesium earcups for mastering and critical listening."
        ),
        "specs": {
            "drivers": "50mm Planar Magnetic",
            "anc": "Studio-grade 45dB ANC",
            "battery": "36 hours",
            "weight": "310g",
        },
    },
    {
        "id": "prod-104",
        "name": "KeyChronos Q1 Mechanical Keyboard",
        "category": "peripherals",
        "price": 189.00,
        "rating": 4.9,
        "stock": 19,
        "badge": "Editor's Choice",
        "description": (
            "75% gasket-mounted CNC aluminum wireless mechanical keyboard with "
            "hot-swappable tactile switches, QMK/VIA programmability, and acoustic foam."
        ),
        "specs": {
            "layout": "75% (82 keys) + Rotary Knob",
            "switches": "Hot-swappable Tactile Panda",
            "connectivity": "2.4GHz / Bluetooth 5.3 / USB-C",
            "chassis": "6063 CNC Machined Aluminum",
        },
    },
    {
        "id": "prod-105",
        "name": "PrecisionGlide Pro Ergonomic Mouse",
        "category": "peripherals",
        "price": 89.00,
        "rating": 4.7,
        "stock": 32,
        "badge": "Ergonomic",
        "description": (
            "Sculpted wireless productivity mouse with electromagnetic free-spin scroll "
            "wheel, quiet optical switches, and 26,000 DPI glass-tracking sensor."
        ),
        "specs": {
            "sensor": "26,000 DPI Darkfield Optical",
            "battery": "70 days via USB-C",
            "buttons": "7 programmable silent buttons",
            "weight": "106g",
        },
    },
    {
        "id": "prod-106",
        "name": "NomadPack 35L Tech Carry-On Backpack",
        "category": "travel",
        "price": 219.00,
        "rating": 4.8,
        "stock": 0,
        "badge": "Out of Stock",
        "description": (
            "Weatherproof Cordura ballistic nylon 35L travel backpack with clamshell "
            "opening, suspended 16-inch laptop vault, and magnetic sternum strap."
        ),
        "specs": {
            "capacity": "35 Liters (Carry-on compliant)",
            "material": "1680D Cordura Ballistic Nylon",
            "laptop_sleeve": "Fits up to 16-inch laptops",
            "weight": "1.45 kg",
        },
    },
    {
        "id": "prod-107",
        "name": "Voyager Carbon 22-Inch Smart Carry-On",
        "category": "travel",
        "price": 279.00,
        "rating": 4.7,
        "stock": 9,
        "badge": "Travel Ready",
        "description": (
            "Aerospace-grade polycarbonate hardshell carry-on roller with silent 360 "
            "Hinamoto spinner wheels, TSA lock, and ejectable 10,000mAh USB-C power bank."
        ),
        "specs": {
            "dimensions": "22 x 14 x 9 inches",
            "shell": "German Makrolon Polycarbonate",
            "battery_bank": "Removable 10,000mAh 30W PD",
            "weight": "3.2 kg",
        },
    },
    {
        "id": "prod-108",
        "name": "LumaView 16-Inch 4K OLED Portable Monitor",
        "category": "monitors",
        "price": 349.00,
        "rating": 4.8,
        "stock": 11,
        "badge": "Creator Gear",
        "description": (
            "Ultra-slim 16-inch 4K+ OLED travel display with 100% DCI-P3 color gamut, "
            "single-cable USB-C video + 65W power pass-through, and magnetic kickstand."
        ),
        "specs": {
            "resolution": "3840 x 2400 (16:10) OLED",
            "brightness": "500 nits HDR TrueBlack",
            "ports": "2x USB-C (DP Alt Mode) + Mini HDMI",
            "weight": "680g",
        },
    },
]

PROMO_CODES: dict[str, dict[str, Any]] = {
    "WEBMCP20": {
        "code": "WEBMCP20",
        "type": "percent",
        "value": 20.0,
        "description": "20% off WebMCP Launch Discount",
    },
    "ADK10": {
        "code": "ADK10",
        "type": "percent",
        "value": 10.0,
        "description": "10% off Google ADK Builder Promo",
    },
    "SAVE25": {
        "code": "SAVE25",
        "type": "fixed",
        "value": 25.0,
        "description": "$25 flat discount on orders over $100",
    },
}

DEFAULT_WEBMCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_products",
        "source": "imperative",
        "api": "navigator.modelContext.registerTool",
        "description": (
            "Search and filter the NexusGear storefront catalog by keyword, category "
            "(audio, peripherals, travel, monitors), maximum price, or stock availability."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword search query"},
                "category": {
                    "type": "string",
                    "description": "Category filter (audio, peripherals, travel, monitors)",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum unit price in USD (0 for no limit)",
                },
                "in_stock_only": {
                    "type": "boolean",
                    "description": "Whether to exclude out-of-stock products",
                },
            },
        },
    },
    {
        "name": "get_product_details",
        "source": "imperative",
        "api": "navigator.modelContext.registerTool",
        "description": (
            "Retrieve complete technical specifications, stock count, and rating "
            "for a product by its product_id (e.g. prod-101)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Product identifier"}
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "add_to_cart",
        "source": "imperative",
        "api": "navigator.modelContext.registerTool",
        "description": "Add a quantity of an in-stock product to the active shopping cart.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Product identifier"},
                "quantity": {"type": "integer", "description": "Quantity (1-10)"},
            },
            "required": ["product_id", "quantity"],
        },
    },
    {
        "name": "remove_from_cart",
        "source": "imperative",
        "api": "navigator.modelContext.registerTool",
        "description": "Remove a product completely from the active shopping cart.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Product identifier"}
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "get_cart",
        "source": "imperative",
        "api": "navigator.modelContext.registerTool",
        "description": (
            "Inspect the active shopping cart items, subtotal, applied promo discount, "
            "shipping details, and final total."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "apply_promo_code",
        "source": "imperative",
        "api": "navigator.modelContext.registerTool",
        "description": "Apply a promotional discount code (e.g. WEBMCP20, ADK10, SAVE25).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Promo code string"}
            },
            "required": ["code"],
        },
    },
    {
        "name": "update_shipping_form",
        "source": "declarative",
        "api": 'HTML <form toolname="update_shipping_form">',
        "description": (
            "Populate the customer's shipping address and delivery speed form on the "
            "checkout page via the Declarative WebMCP HTML Form API."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string", "description": "Recipient full name"},
                "email": {"type": "string", "description": "Contact email address"},
                "address": {
                    "type": "string",
                    "description": "Street, city, state, ZIP",
                },
                "delivery_speed": {
                    "type": "string",
                    "enum": ["standard", "express", "overnight"],
                    "description": "Shipping speed",
                },
            },
            "required": ["full_name", "email", "address", "delivery_speed"],
        },
    },
    {
        "name": "checkout_order",
        "source": "imperative",
        "api": "navigator.modelContext.registerTool",
        "description": (
            "Submit and finalize purchase for the active shopping cart. Irreversible "
            "action — requires explicit user confirmation first."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string", "description": "Recipient full name"},
                "address": {"type": "string", "description": "Full shipping address"},
                "user_confirmed": {
                    "type": "boolean",
                    "description": "True only after explicit user confirmation",
                },
            },
            "required": ["full_name", "address", "user_confirmed"],
        },
    },
]

DELIVERY_FEES: dict[str, float] = {
    "standard": 0.0,
    "express": 15.0,
    "overnight": 29.0,
}


class WebMcpStore:
    """Deterministic state store backing the WebMCP storefront and headless runs."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset catalog, carts, shipping forms, and orders to initial state."""
        self._products: dict[str, dict[str, Any]] = {
            item["id"]: copy.deepcopy(item) for item in CATALOG
        }
        self._sessions: dict[str, dict[str, Any]] = {}
        self._registered_tools: list[dict[str, Any]] = copy.deepcopy(
            DEFAULT_WEBMCP_TOOLS
        )
        self._activity_log: list[dict[str, Any]] = []

    def _session(self, session_id: str) -> dict[str, Any]:
        sid = session_id or "default"
        if sid not in self._sessions:
            self._sessions[sid] = {
                "cart": {},  # product_id -> quantity
                "promo_code": None,
                "shipping": {
                    "full_name": "",
                    "email": "",
                    "address": "",
                    "delivery_speed": "standard",
                },
                "orders": [],
                "active_filters": {
                    "query": "",
                    "category": "",
                    "max_price": 0.0,
                    "in_stock_only": False,
                },
            }
        return self._sessions[sid]

    def record_activity(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any],
        transport: str = "synchronized_store",
    ) -> None:
        """Append a WebMCP tool execution entry to the inspector log."""
        entry = {
            "id": f"evt-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "tool": tool_name,
            "args": args,
            "status": result.get("status", "success"),
            "transport": transport,
        }
        self._activity_log.append(entry)
        if len(self._activity_log) > 100:
            self._activity_log = self._activity_log[-100:]

    def get_registered_tools(self) -> list[dict[str, Any]]:
        """Return currently exposed WebMCP tool definitions."""
        return copy.deepcopy(self._registered_tools)

    def set_registered_tools(self, tools: list[dict[str, Any]]) -> None:
        """Update registered tools announced by a live browser's modelContext."""
        if tools:
            self._registered_tools = copy.deepcopy(tools)

    def get_catalog(self) -> list[dict[str, Any]]:
        """Return all catalog products."""
        return [copy.deepcopy(p) for p in self._products.values()]

    def get_snapshot(self, session_id: str = "default") -> dict[str, Any]:
        """Return complete UI state snapshot for browser synchronization."""
        sess = self._session(session_id)
        return {
            "session_id": session_id or "default",
            "catalog": self.get_catalog(),
            "cart": self._compute_cart_summary(sess),
            "shipping": copy.deepcopy(sess["shipping"]),
            "active_filters": copy.deepcopy(sess["active_filters"]),
            "orders": copy.deepcopy(sess["orders"]),
            "registered_tools": self.get_registered_tools(),
            "activity_log": copy.deepcopy(self._activity_log[-25:]),
        }

    def sync_from_browser(
        self, payload: dict[str, Any], session_id: str = "default"
    ) -> None:
        """Synchronize browser-side manual interactions back into the Python store."""
        sess = self._session(session_id)
        if "cart_items" in payload and isinstance(payload["cart_items"], dict):
            clean_cart: dict[str, int] = {}
            for pid, qty in payload["cart_items"].items():
                if pid in self._products and int(qty) > 0:
                    clean_cart[pid] = int(qty)
            sess["cart"] = clean_cart
        if "promo_code" in payload:
            code = (payload.get("promo_code") or "").strip().upper()
            sess["promo_code"] = code if code in PROMO_CODES else None
        if "shipping" in payload and isinstance(payload["shipping"], dict):
            for key in ("full_name", "email", "address", "delivery_speed"):
                if key in payload["shipping"]:
                    sess["shipping"][key] = str(payload["shipping"][key])

    def _compute_cart_summary(self, sess: dict[str, Any]) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        subtotal = 0.0
        total_quantity = 0
        for pid, qty in sess["cart"].items():
            product = self._products.get(pid)
            if not product or qty <= 0:
                continue
            line_total = round(product["price"] * qty, 2)
            subtotal = round(subtotal + line_total, 2)
            total_quantity += qty
            items.append(
                {
                    "product_id": pid,
                    "name": product["name"],
                    "unit_price": product["price"],
                    "quantity": qty,
                    "line_total": line_total,
                }
            )

        discount = 0.0
        promo_code = sess.get("promo_code")
        promo_info = PROMO_CODES.get(promo_code) if promo_code else None
        if promo_info and subtotal > 0:
            if promo_info["type"] == "percent":
                discount = round(subtotal * (promo_info["value"] / 100.0), 2)
            elif promo_info["type"] == "fixed" and subtotal >= 100.0:
                discount = min(subtotal, float(promo_info["value"]))

        speed = sess["shipping"].get("delivery_speed", "standard")
        shipping_fee = DELIVERY_FEES.get(speed, 0.0) if subtotal > 0 else 0.0
        total = round(max(0.0, subtotal - discount) + shipping_fee, 2)

        return {
            "items": items,
            "item_count": total_quantity,
            "subtotal": subtotal,
            "promo_code": promo_code,
            "promo_description": promo_info["description"] if promo_info else None,
            "discount": discount,
            "delivery_speed": speed,
            "shipping_fee": shipping_fee,
            "total": total,
            "currency": "USD",
        }

    def search_products(
        self,
        query: str = "",
        category: str = "",
        max_price: float = 0.0,
        in_stock_only: bool = False,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Execute WebMCP search_products tool."""
        sess = self._session(session_id)
        q_norm = query.strip().lower()
        cat_norm = category.strip().lower()
        if cat_norm in ("all", "any", "*"):
            cat_norm = ""

        sess["active_filters"] = {
            "query": query.strip(),
            "category": cat_norm,
            "max_price": float(max_price or 0.0),
            "in_stock_only": bool(in_stock_only),
        }

        tokens = [
            tok.rstrip("s") if len(tok) > 4 else tok
            for tok in q_norm.replace("-", " ").split()
            if tok not in {"and", "the", "for", "with", "under", "any"}
        ]

        matches: list[dict[str, Any]] = []
        for product in self._products.values():
            if cat_norm and product["category"].lower() != cat_norm:
                continue
            if max_price and max_price > 0 and product["price"] > max_price:
                continue
            if in_stock_only and product["stock"] <= 0:
                continue
            if tokens:
                haystack = (
                    f"{product['name']} {product['category']} {product['description']} "
                    f"{' '.join(str(v) for v in product['specs'].values())}"
                ).lower()
                haystack_norm = haystack.replace("-", " ")
                if not all(tok in haystack or tok in haystack_norm for tok in tokens):
                    continue
            matches.append(
                {
                    "product_id": product["id"],
                    "name": product["name"],
                    "category": product["category"],
                    "price": product["price"],
                    "rating": product["rating"],
                    "stock": product["stock"],
                    "in_stock": product["stock"] > 0,
                    "badge": product["badge"],
                    "description": product["description"],
                }
            )

        return {
            "status": "success",
            "count": len(matches),
            "filters_applied": copy.deepcopy(sess["active_filters"]),
            "products": matches,
        }

    def get_product_details(self, product_id: str) -> dict[str, Any]:
        """Execute WebMCP get_product_details tool."""
        pid = product_id.strip()
        product = self._products.get(pid)
        if not product:
            # Fallback case-insensitive ID or exact name lookup
            for candidate in self._products.values():
                if (
                    candidate["id"].lower() == pid.lower()
                    or candidate["name"].lower() == pid.lower()
                ):
                    product = candidate
                    break
        if not product:
            return {
                "status": "error",
                "error": f"Product '{product_id}' not found in catalog.",
                "available_product_ids": list(self._products.keys()),
            }
        return {
            "status": "success",
            "product": copy.deepcopy(product),
        }

    def add_to_cart(
        self,
        product_id: str,
        quantity: int = 1,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Execute WebMCP add_to_cart tool."""
        pid = product_id.strip()
        product = self._products.get(pid)
        if not product:
            for candidate in self._products.values():
                if (
                    candidate["id"].lower() == pid.lower()
                    or pid.lower() in candidate["name"].lower()
                ):
                    product = candidate
                    pid = candidate["id"]
                    break
        if not product:
            return {
                "status": "error",
                "error": f"Product '{product_id}' does not exist.",
            }
        if quantity <= 0 or quantity > 10:
            return {
                "status": "error",
                "error": "Quantity must be between 1 and 10.",
            }
        if product["stock"] <= 0:
            return {
                "status": "error",
                "error": f"'{product['name']}' ({pid}) is currently out of stock.",
            }

        sess = self._session(session_id)
        new_qty = sess["cart"].get(pid, 0) + int(quantity)
        if new_qty > product["stock"]:
            return {
                "status": "error",
                "error": (
                    f"Requested quantity ({new_qty}) exceeds available stock "
                    f"({product['stock']}) for '{product['name']}'."
                ),
            }

        sess["cart"][pid] = new_qty
        # Also mirror into "default" session so a connected storefront tab shows it
        if session_id and session_id != "default":
            default_sess = self._session("default")
            default_sess["cart"][pid] = new_qty

        cart_summary = self._compute_cart_summary(sess)
        return {
            "status": "success",
            "message": f"Added {quantity}x {product['name']} to cart.",
            "added_product": {
                "product_id": pid,
                "name": product["name"],
                "quantity_added": int(quantity),
                "unit_price": product["price"],
            },
            "cart": cart_summary,
        }

    def remove_from_cart(
        self,
        product_id: str,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Execute WebMCP remove_from_cart tool."""
        pid = product_id.strip()
        sess = self._session(session_id)
        if pid not in sess["cart"]:
            return {
                "status": "error",
                "error": f"Product '{pid}' is not currently in the cart.",
                "cart": self._compute_cart_summary(sess),
            }
        removed_name = self._products[pid]["name"]
        del sess["cart"][pid]
        if session_id and session_id != "default":
            self._session("default")["cart"].pop(pid, None)
        return {
            "status": "success",
            "message": f"Removed '{removed_name}' from cart.",
            "cart": self._compute_cart_summary(sess),
        }

    def get_cart(self, session_id: str = "default") -> dict[str, Any]:
        """Execute WebMCP get_cart tool."""
        sess = self._session(session_id)
        return {
            "status": "success",
            "cart": self._compute_cart_summary(sess),
            "shipping": copy.deepcopy(sess["shipping"]),
        }

    def apply_promo_code(
        self,
        code: str,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Execute WebMCP apply_promo_code tool."""
        normalized = code.strip().upper()
        promo = PROMO_CODES.get(normalized)
        sess = self._session(session_id)
        if not promo:
            return {
                "status": "error",
                "error": (
                    f"Invalid promo code '{code}'. Valid codes include WEBMCP20, "
                    "ADK10, and SAVE25."
                ),
                "cart": self._compute_cart_summary(sess),
            }
        sess["promo_code"] = normalized
        if session_id and session_id != "default":
            self._session("default")["promo_code"] = normalized
        summary = self._compute_cart_summary(sess)
        return {
            "status": "success",
            "message": f"Applied promo code {normalized}: {promo['description']}.",
            "cart": summary,
        }

    def update_shipping_form(
        self,
        full_name: str,
        email: str,
        address: str,
        delivery_speed: str = "standard",
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Execute Declarative WebMCP update_shipping_form HTML form tool."""
        speed = delivery_speed.strip().lower() or "standard"
        if speed not in DELIVERY_FEES:
            return {
                "status": "error",
                "error": (
                    f"Unsupported delivery_speed '{delivery_speed}'. "
                    "Choose 'standard', 'express', or 'overnight'."
                ),
            }
        shipping_data = {
            "full_name": full_name.strip(),
            "email": email.strip(),
            "address": address.strip(),
            "delivery_speed": speed,
        }
        sess = self._session(session_id)
        sess["shipping"] = copy.deepcopy(shipping_data)
        if session_id and session_id != "default":
            self._session("default")["shipping"] = copy.deepcopy(shipping_data)
        return {
            "status": "success",
            "webmcp_source": "declarative_form",
            "message": "Shipping form populated via Declarative WebMCP HTML API.",
            "shipping": shipping_data,
            "cart": self._compute_cart_summary(sess),
        }

    def checkout_order(
        self,
        full_name: str,
        address: str,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Execute WebMCP checkout_order tool once guardrails have passed."""
        sess = self._session(session_id)
        summary = self._compute_cart_summary(sess)
        if not summary["items"]:
            return {
                "status": "error",
                "error": (
                    "Cannot checkout an empty cart. Add at least one product to "
                    "the cart first."
                ),
            }
        if not full_name.strip() or not address.strip():
            return {
                "status": "error",
                "error": "Both full_name and shipping address are required for checkout.",
            }

        # Deduct stock
        for item in summary["items"]:
            pid = item["product_id"]
            self._products[pid]["stock"] = max(
                0, self._products[pid]["stock"] - item["quantity"]
            )

        order_id = f"NXG-{uuid.uuid4().hex[:6].upper()}"
        order_record = {
            "order_id": order_id,
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "recipient": full_name.strip(),
            "shipping_address": address.strip(),
            "delivery_speed": summary["delivery_speed"],
            "items": summary["items"],
            "subtotal": summary["subtotal"],
            "promo_code": summary["promo_code"],
            "discount": summary["discount"],
            "shipping_fee": summary["shipping_fee"],
            "total_charged": summary["total"],
            "currency": "USD",
        }
        sess["orders"].append(order_record)
        sess["cart"] = {}
        sess["promo_code"] = None
        if session_id and session_id != "default":
            default_sess = self._session("default")
            default_sess["orders"].append(copy.deepcopy(order_record))
            default_sess["cart"] = {}
            default_sess["promo_code"] = None

        return {
            "status": "success",
            "message": (
                f"Order {order_id} placed successfully for {full_name.strip()}!"
            ),
            "order": order_record,
        }

    def execute_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        session_id: str = "default",
        transport: str = "synchronized_store",
    ) -> dict[str, Any]:
        """Dispatch any WebMCP tool by name and record activity."""
        if tool_name == "search_products":
            res = self.search_products(
                query=str(args.get("query", "")),
                category=str(args.get("category", "")),
                max_price=float(args.get("max_price", 0.0) or 0.0),
                in_stock_only=bool(args.get("in_stock_only", False)),
                session_id=session_id,
            )
        elif tool_name == "get_product_details":
            res = self.get_product_details(product_id=str(args.get("product_id", "")))
        elif tool_name == "add_to_cart":
            res = self.add_to_cart(
                product_id=str(args.get("product_id", "")),
                quantity=int(args.get("quantity", 1)),
                session_id=session_id,
            )
        elif tool_name == "remove_from_cart":
            res = self.remove_from_cart(
                product_id=str(args.get("product_id", "")),
                session_id=session_id,
            )
        elif tool_name == "get_cart":
            res = self.get_cart(session_id=session_id)
        elif tool_name == "apply_promo_code":
            res = self.apply_promo_code(
                code=str(args.get("code", "")),
                session_id=session_id,
            )
        elif tool_name == "update_shipping_form":
            res = self.update_shipping_form(
                full_name=str(args.get("full_name", "")),
                email=str(args.get("email", "")),
                address=str(args.get("address", "")),
                delivery_speed=str(args.get("delivery_speed", "standard")),
                session_id=session_id,
            )
        elif tool_name == "checkout_order":
            res = self.checkout_order(
                full_name=str(args.get("full_name", "")),
                address=str(args.get("address", "")),
                session_id=session_id,
            )
        else:
            res = {
                "status": "error",
                "error": f"Unknown WebMCP tool '{tool_name}'.",
            }

        self.record_activity(tool_name, args, res, transport=transport)
        return res


store = WebMcpStore()
