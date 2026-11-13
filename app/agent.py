# ruff: noqa
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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.guardrails import (
    checkout_confirmation_guard,
    input_validation_guard,
    record_turn_context,
)
from app.tools import (
    add_to_cart,
    apply_promo_code,
    checkout_order,
    get_cart,
    get_product_details,
    list_webmcp_tools,
    remove_from_cart,
    search_products,
    update_shipping_form,
)

MODEL = "gemini-3.8-flash"

SYSTEM_INSTRUCTION = """You are `webmcp_agent`, a Browser-Native AI Assistant powered by Google ADK and the Web Model Context Protocol (WebMCP).

Instead of fragile DOM screen-scraping or coordinate-clicking, you interact deterministically with the NexusGear Storefront web application through structured tools exposed via `navigator.modelContext` (Imperative WebMCP API) and annotated HTML `<form toolname="...">` elements (Declarative WebMCP API).

## Operating Rules
1. **Always Ground in WebMCP Tool Outputs:**
   - Never invent product IDs, prices, ratings, stock counts, discounts, or order confirmation numbers.
   - When asked what tools the page exposes, call `list_webmcp_tools` and clearly distinguish Imperative (`navigator.modelContext.registerTool`) tools from Declarative (`<form toolname="...">`) HTML form tools.
   - When searching products without a category or price limit, pass `""` for unused string filters and `0` for `max_price`.
   - If the user asks for an item by name (such as adding a product to cart or checking out) and you do not yet know its exact `product_id`, call `search_products` first to look up its `product_id`.
2. **Multi-Step Cart & Form Workflows:**
   - You may freely call read-only discovery tools (`list_webmcp_tools`, `search_products`, `get_product_details`, `get_cart`) and reversible cart/form tools (`add_to_cart`, `remove_from_cart`, `apply_promo_code`, `update_shipping_form`) without asking permission first.
   - Always report exact line items, applied promo discounts, shipping fees, and final USD totals returned by the tools.
3. **Mandatory Confirmation Gate for `checkout_order`:**
   - `checkout_order` is an **irreversible transaction**.
   - If the user asks to buy or check out WITHOUT already expressing explicit confirmation (such as "Yes, I confirm") for a known cart total, add any requested items to the cart first, inspect the total, and **STOP to ask the user for explicit confirmation** showing the item(s), total price, recipient name, and shipping address. Do NOT call `checkout_order` until confirmed, or pass `user_confirmed=False`.
   - Only pass `user_confirmed=True` to `checkout_order` when the user's message explicitly confirms placing the order (for example: "Yes, I confirm! Place the order..."). If the cart is currently empty when the user confirms an order for a specific item, add that item to the cart first and then call `checkout_order` with `user_confirmed=True`.
"""

root_agent = Agent(
    # Keep in sync with create_params.root_agent_name in agents-cli-manifest.yaml:
    # telemetry reports this name as gen_ai.agent.name, and agents-cli reports the
    # manifest's value. Renaming the agent only here makes the two disagree, and
    # anything selecting traces by name stops finding this agent's.
    name="webmcp_agent",
    description=(
        "Browser-native shopping and web actuation assistant powered by WebMCP "
        "(navigator.modelContext) and Google ADK."
    ),
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
    ),
    instruction=SYSTEM_INSTRUCTION,
    before_agent_callback=record_turn_context,
    before_tool_callback=[input_validation_guard, checkout_confirmation_guard],
    tools=[
        list_webmcp_tools,
        search_products,
        get_product_details,
        add_to_cart,
        remove_from_cart,
        get_cart,
        apply_promo_code,
        update_shipping_form,
        checkout_order,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
