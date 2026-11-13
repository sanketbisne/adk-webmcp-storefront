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

"""Standalone launcher for the WebMCP Bridge + Storefront Demo Server."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.webmcp_bridge import webmcp_router

bridge_app = FastAPI(
    title="WebMCP Bridge & NexusGear Storefront",
    description="Relays browser navigator.modelContext tools to Google ADK agents.",
)
bridge_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
bridge_app.include_router(webmcp_router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("WEBMCP_PORT", "8765"))
    uvicorn.run(bridge_app, host="127.0.0.1", port=port)
