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

"""WebMCP WebSocket & REST Bridge connecting browser modelContext tools to ADK."""

from __future__ import annotations

import asyncio
import logging
import os
import pathlib
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.webmcp_store import store

logger = logging.getLogger(__name__)

FRONTEND_DIR = pathlib.Path(__file__).resolve().parent.parent / "frontend"


class ToolCallPayload(BaseModel):
    """REST payload for invoking a WebMCP tool through the bridge."""

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    session_id: str = "default"


class WebMcpBridgeManager:
    """Manages active browser WebSocket clients exposing navigator.modelContext tools."""

    def __init__(self) -> None:
        self._clients: dict[str, WebSocket] = {}
        self._pending_calls: dict[str, asyncio.Future[dict[str, Any]]] = {}

    @property
    def connected_tabs(self) -> int:
        return len(self._clients)

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients[client_id] = websocket
        logger.info("WebMCP browser tab connected: %s", client_id)
        await websocket.send_json(
            {
                "type": "webmcp:init",
                "clientId": client_id,
                "snapshot": store.get_snapshot("default"),
            }
        )

    def disconnect(self, client_id: str) -> None:
        self._clients.pop(client_id, None)
        logger.info("WebMCP browser tab disconnected: %s", client_id)

    async def broadcast_snapshot(self, session_id: str = "default") -> None:
        if not self._clients:
            return
        snapshot = store.get_snapshot(session_id)
        stale: list[str] = []
        for cid, ws in list(self._clients.items()):
            try:
                await ws.send_json({"type": "webmcp:state_sync", "snapshot": snapshot})
            except Exception:
                stale.append(cid)
        for cid in stale:
            self.disconnect(cid)

    async def handle_message(self, client_id: str, message: dict[str, Any]) -> None:
        msg_type = message.get("type", "")
        if msg_type == "webmcp:register_tools":
            tools = message.get("tools", [])
            if isinstance(tools, list) and tools:
                store.set_registered_tools(tools)
                logger.info(
                    "Registered %d WebMCP tools from browser tab %s",
                    len(tools),
                    client_id,
                )
        elif msg_type == "webmcp:sync_state":
            payload = message.get("state", {})
            if isinstance(payload, dict):
                store.sync_from_browser(payload, session_id="default")
        elif msg_type == "webmcp:tool_result":
            call_id = str(message.get("callId", ""))
            fut = self._pending_calls.get(call_id)
            if fut and not fut.done():
                result = message.get("result")
                fut.set_result(
                    result
                    if isinstance(result, dict)
                    else {"status": "success", "result": result}
                )

    async def execute_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Execute a WebMCP tool on a live connected browser tab or fallback store."""
        # Keep synchronized Python store updated first for deterministic consistency
        canonical_result = store.execute_tool(
            tool_name=tool_name,
            args=args,
            session_id=session_id,
            transport="live_browser_ws" if self._clients else "synchronized_store",
        )

        if not self._clients:
            return canonical_result

        # Dispatch WebMCP RPC call to the most recently connected active browser tab
        target_cid, target_ws = next(reversed(self._clients.items()))
        call_id = f"call-{uuid.uuid4().hex[:10]}"
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_calls[call_id] = fut

        try:
            await target_ws.send_json(
                {
                    "type": "webmcp:call_tool",
                    "callId": call_id,
                    "tool": tool_name,
                    "args": args,
                    "canonicalResult": canonical_result,
                    "snapshot": store.get_snapshot(session_id),
                }
            )
            browser_result = await asyncio.wait_for(fut, timeout=4.0)
            # Broadcast updated state to any other open storefront tabs
            if len(self._clients) > 1:
                await self.broadcast_snapshot(session_id)
            if isinstance(browser_result, dict) and browser_result.get("status"):
                browser_result.setdefault("webmcp_transport", "live_browser_ws")
                return browser_result
            return canonical_result
        except Exception as exc:
            logger.warning(
                "Browser WebMCP RPC timed out or failed on %s (%s); using store result.",
                target_cid,
                exc,
            )
            return canonical_result
        finally:
            self._pending_calls.pop(call_id, None)


bridge_manager = WebMcpBridgeManager()
webmcp_router = APIRouter(tags=["webmcp"])


@webmcp_router.get("/webmcp", include_in_schema=False)
async def serve_webmcp_storefront() -> FileResponse:
    """Serve the interactive WebMCP NexusGear Storefront demo page."""
    return FileResponse(FRONTEND_DIR / "index.html")


@webmcp_router.get("/webmcp-assets/{filename}", include_in_schema=False)
async def serve_webmcp_asset(filename: str) -> FileResponse:
    """Serve static JS/CSS assets for the WebMCP Storefront."""
    safe_name = pathlib.Path(filename).name
    target = FRONTEND_DIR / safe_name
    if not target.is_file():
        return JSONResponse({"error": "Asset not found"}, status_code=404)  # type: ignore[return-value]
    return FileResponse(target)


@webmcp_router.get("/api/webmcp/status")
async def get_webmcp_status() -> dict[str, Any]:
    """Return live connection status and registered WebMCP tool count."""
    tools = store.get_registered_tools()
    return {
        "status": "online",
        "connected_browser_tabs": bridge_manager.connected_tabs,
        "registered_tool_count": len(tools),
        "imperative_tools": [
            t["name"] for t in tools if t.get("source") == "imperative"
        ],
        "declarative_tools": [
            t["name"] for t in tools if t.get("source") == "declarative"
        ],
    }


@webmcp_router.get("/api/webmcp/tools")
async def list_registered_webmcp_tools() -> dict[str, Any]:
    """Return JSON schemas for all exposed WebMCP tools."""
    return {
        "status": "success",
        "connected_browser_tabs": bridge_manager.connected_tabs,
        "tools": store.get_registered_tools(),
    }


@webmcp_router.get("/api/webmcp/state")
async def get_webmcp_state(session_id: str = "default") -> dict[str, Any]:
    """Return current storefront catalog, cart, shipping form, and inspector log."""
    return store.get_snapshot(session_id)


@webmcp_router.post("/api/webmcp/reset")
async def reset_webmcp_state() -> dict[str, Any]:
    """Reset storefront state to clean defaults."""
    store.reset()
    await bridge_manager.broadcast_snapshot("default")
    return {"status": "success", "snapshot": store.get_snapshot("default")}


@webmcp_router.post("/api/webmcp/call")
async def invoke_webmcp_tool_http(payload: ToolCallPayload) -> dict[str, Any]:
    """Invoke a WebMCP tool over HTTP (used by external CLI agent processes)."""
    return await bridge_manager.execute_tool(
        tool_name=payload.tool_name,
        args=payload.args,
        session_id=payload.session_id,
    )


@webmcp_router.websocket("/ws/webmcp")
async def webmcp_websocket_endpoint(websocket: WebSocket) -> None:
    """Bi-directional WebSocket channel for browser navigator.modelContext SDK."""
    client_id = f"tab-{uuid.uuid4().hex[:8]}"
    await bridge_manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict):
                await bridge_manager.handle_message(client_id, data)
    except WebSocketDisconnect:
        bridge_manager.disconnect(client_id)
    except Exception as exc:
        logger.debug("WebSocket closed for %s: %s", client_id, exc)
        bridge_manager.disconnect(client_id)


async def dispatch_webmcp_tool(
    tool_name: str,
    args: dict[str, Any],
    session_id: str = "default",
) -> dict[str, Any]:
    """Dispatch a WebMCP tool call via in-process WS, remote bridge, or local store."""
    # 1. If a browser tab is connected directly to this process, relay immediately.
    if bridge_manager.connected_tabs > 0:
        return await bridge_manager.execute_tool(tool_name, args, session_id)

    # 2. Check if an external bridge server (e.g. port 8765) has a connected tab.
    remote_url = os.getenv("WEBMCP_BRIDGE_URL", "").strip()
    if remote_url:
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.post(
                    f"{remote_url.rstrip('/')}/api/webmcp/call",
                    json={
                        "tool_name": tool_name,
                        "args": args,
                        "session_id": session_id,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass

    # 3. Deterministic local store execution (used in CLI / eval / headless runs).
    return await bridge_manager.execute_tool(tool_name, args, session_id)
