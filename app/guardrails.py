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

"""ADK before_agent and before_tool safety guardrails for WebMCP actuation."""

from __future__ import annotations

import re
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool, ToolContext

from app.webmcp_store import store

UNSAFE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<\s*script\b", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"\bon(?:error|load|click|mouseover)\s*=", re.IGNORECASE),
)

NEGATION_PATTERN = re.compile(
    r"\b(?:do\s+not|don't|dont|never|cancel|stop|abort|wait)\b",
    re.IGNORECASE,
)

CONFIRMATION_PATTERN = re.compile(
    r"\b(?:yes|confirm|confirmed|i\s+confirm|approve|approved|go\s+ahead|proceed)\b",
    re.IGNORECASE,
)


def extract_content_text(content: Any) -> str:
    """Extract concatenated text from a google.genai Content object."""
    if content is None:
        return ""
    parts = getattr(content, "parts", None) or []
    texts: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
    return " ".join(texts)


def has_explicit_confirmation(user_text: str) -> bool:
    """Return True only when user text expresses affirmative checkout approval."""
    cleaned = user_text.strip()
    if not cleaned:
        return False
    if NEGATION_PATTERN.search(cleaned):
        return False
    return bool(CONFIRMATION_PATTERN.search(cleaned))


async def record_turn_context(callback_context: CallbackContext) -> None:
    """Capture current turn's user message and session ID before agent runs."""
    user_text = extract_content_text(callback_context.user_content)
    callback_context.state["latest_user_message"] = user_text
    session = getattr(callback_context, "session", None)
    session_id = getattr(session, "id", None) or "default"
    callback_context.state["webmcp_session_id"] = session_id


async def input_validation_guard(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any] | None:
    """Validate WebMCP tool inputs for script injection and numeric bounds."""
    del tool_context  # Unused in stateless input checks

    for key, value in args.items():
        if isinstance(value, str):
            for pattern in UNSAFE_PATTERNS:
                if pattern.search(value):
                    return {
                        "status": "blocked",
                        "error": (
                            f"Guardrail blocked unsafe input in argument '{key}': "
                            "executable HTML/script payloads are not permitted."
                        ),
                    }

    if tool.name == "add_to_cart":
        raw_qty = args.get("quantity")
        try:
            qty = int(raw_qty)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return {
                "status": "blocked",
                "error": "Invalid quantity: quantity must be an integer between 1 and 10.",
            }
        if qty < 1 or qty > 10:
            return {
                "status": "blocked",
                "error": (
                    f"Guardrail blocked add_to_cart(quantity={qty}): "
                    "quantity must be between 1 and 10 per call."
                ),
            }

    return None


async def checkout_confirmation_guard(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any] | None:
    """Require explicit user confirmation before executing checkout_order."""
    if tool.name != "checkout_order":
        return None

    session = getattr(tool_context, "session", None)
    session_id = (
        tool_context.state.get("webmcp_session_id")
        or getattr(session, "id", None)
        or "default"
    )
    user_text = extract_content_text(
        getattr(tool_context, "user_content", None)
    ) or str(tool_context.state.get("latest_user_message", ""))

    user_confirmed_flag = args.get("user_confirmed") is True
    explicit_intent = has_explicit_confirmation(user_text)

    if not user_confirmed_flag or not explicit_intent:
        cart_snapshot = store.get_cart(session_id=session_id)["cart"]
        return {
            "status": "confirmation_required",
            "error": (
                "CHECKOUT BLOCKED BY SAFETY GUARDRAIL: Irreversible WebMCP tool "
                "'checkout_order' requires explicit user confirmation. Do NOT retry "
                "checkout_order in this turn. Summarize the cart items, final total, "
                "recipient name, and shipping address, and ask the user to reply with "
                "'Yes, I confirm' to place the order."
            ),
            "cart_summary": cart_snapshot,
            "proposed_recipient": args.get("full_name", ""),
            "proposed_address": args.get("address", ""),
        }

    return None
