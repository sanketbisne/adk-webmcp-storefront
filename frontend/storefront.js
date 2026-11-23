/**
 * NexusGear Storefront Application
 * Registers Imperative WebMCP tools via navigator.modelContext.registerTool(...)
 * and coordinates real-time visual UI updates + ADK /run_sse Copilot chat.
 */
(function () {
  "use strict";

  const state = {
    catalog: [],
    cart: {
      items: [],
      item_count: 0,
      subtotal: 0,
      promo_code: null,
      discount: 0,
      shipping_fee: 0,
      total: 0,
    },
    shipping: {
      full_name: "",
      email: "",
      address: "",
      delivery_speed: "standard",
    },
    filters: {
      query: "",
      category: "",
      max_price: 0,
      in_stock_only: false,
    },
    orders: [],
    highlightedIds: new Set(),
    adkUserId: "browser_user",
    adkSessionId: null,
  };

  const els = {
    bridgeDot: document.getElementById("bridgeDot"),
    bridgeStatusText: document.getElementById("bridgeStatusText"),
    toolCountBadge: document.getElementById("toolCountBadge"),
    resetBtn: document.getElementById("resetBtn"),
    searchInput: document.getElementById("searchInput"),
    categoryPills: document.getElementById("categoryPills"),
    maxPriceInput: document.getElementById("maxPriceInput"),
    inStockCheckbox: document.getElementById("inStockCheckbox"),
    catalogGrid: document.getElementById("catalogGrid"),
    shippingForm: document.getElementById("shippingForm"),
    toggleMarkupBtn: document.getElementById("toggleMarkupBtn"),
    markupPreview: document.getElementById("markupPreview"),
    cartCountTab: document.getElementById("cartCountTab"),
    cartSummaryBox: document.getElementById("cartSummaryBox"),
    manualPromoInput: document.getElementById("manualPromoInput"),
    applyPromoBtn: document.getElementById("applyPromoBtn"),
    ordersList: document.getElementById("ordersList"),
    registeredSchemasList: document.getElementById("registeredSchemasList"),
    rpcEventList: document.getElementById("rpcEventList"),
    chatMessages: document.getElementById("chatMessages"),
    chatForm: document.getElementById("chatForm"),
    chatInput: document.getElementById("chatInput"),
    toast: document.getElementById("toast"),
  };

  let toastTimer = null;
  function showToast(text) {
    els.toast.textContent = text;
    els.toast.classList.add("visible");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => els.toast.classList.remove("visible"), 2800);
  }

  function highlightProducts(ids) {
    state.highlightedIds = new Set(ids);
    renderCatalog();
    setTimeout(() => {
      state.highlightedIds.clear();
      renderCatalog();
    }, 2400);
  }

  function filteredProducts() {
    const q = (state.filters.query || "").trim().toLowerCase();
    const cat = (state.filters.category || "").trim().toLowerCase();
    const maxP = Number(state.filters.max_price || 0);
    const stockOnly = Boolean(state.filters.in_stock_only);

    const tokens = q
      .replace(/-/g, " ")
      .split(/\s+/)
      .filter((t) => t && !["and", "the", "for", "with", "under", "any"].includes(t))
      .map((t) => (t.length > 4 ? t.replace(/s$/, "") : t));

    return state.catalog.filter((p) => {
      if (cat && p.category.toLowerCase() !== cat) return false;
      if (maxP > 0 && p.price > maxP) return false;
      if (stockOnly && p.stock <= 0) return false;
      if (tokens.length > 0) {
        const hay = `${p.name} ${p.category} ${p.description} ${Object.values(
          p.specs || {}
        ).join(" ")}`
          .toLowerCase()
          .replace(/-/g, " ");
        if (!tokens.every((tok) => hay.includes(tok))) return false;
      }
      return true;
    });
  }

  function renderFilters() {
    els.searchInput.value = state.filters.query || "";
    els.maxPriceInput.value = state.filters.max_price || 0;
    els.inStockCheckbox.checked = Boolean(state.filters.in_stock_only);
    els.categoryPills.querySelectorAll(".cat-pill").forEach((btn) => {
      btn.classList.toggle(
        "active",
        (btn.dataset.cat || "") === (state.filters.category || "")
      );
    });
  }

  function renderCatalog() {
    const items = filteredProducts();
    if (items.length === 0) {
      els.catalogGrid.innerHTML =
        '<div style="color:#94a3b8;padding:20px;">No products match the active WebMCP filter criteria.</div>';
      return;
    }

    els.catalogGrid.innerHTML = items
      .map((p) => {
        const oos = p.stock <= 0;
        const hl = state.highlightedIds.has(p.id) ? "agent-highlight" : "";
        const specs = Object.values(p.specs || {})
          .slice(0, 3)
          .map((s) => `<span class="spec-chip">${escapeHtml(String(s))}</span>`)
          .join("");
        return `
          <article class="product-card ${hl}" data-id="${escapeHtml(p.id)}">
            <div class="card-top">
              <span class="prod-id">${escapeHtml(p.id)} · ★ ${p.rating}</span>
              <span class="badge ${oos ? "oos" : ""}">${escapeHtml(
          oos ? "Out of Stock" : p.badge
        )}</span>
            </div>
            <h3>${escapeHtml(p.name)}</h3>
            <p class="prod-desc">${escapeHtml(p.description)}</p>
            <div class="specs-row">${specs}</div>
            <div class="card-footer">
              <div>
                <div class="price">$${Number(p.price).toFixed(2)}</div>
                <div class="stock-meta">${
                  oos ? "0 available" : `${p.stock} in stock`
                }</div>
              </div>
              <button class="btn ${
                oos ? "" : "btn-primary"
              } add-btn" data-id="${escapeHtml(p.id)}" ${oos ? "disabled" : ""}>
                ${oos ? "Sold Out" : "+ Add to Cart"}
              </button>
            </div>
          </article>
        `;
      })
      .join("");

    els.catalogGrid.querySelectorAll(".add-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const pid = btn.dataset.id;
        await fetch("/api/webmcp/call", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tool_name: "add_to_cart",
            args: { product_id: pid, quantity: 1 },
          }),
        });
      });
    });
  }

  function renderCartAndOrders() {
    const c = state.cart;
    els.cartCountTab.textContent = String(c.item_count || 0);

    if (!c.items || c.items.length === 0) {
      els.cartSummaryBox.innerHTML =
        '<div style="color:#94a3b8;">Your WebMCP cart is currently empty.</div>';
    } else {
      const lines = c.items
        .map(
          (item) => `
          <div class="cart-line">
            <div>
              <strong>${escapeHtml(item.name)}</strong>
              <div style="color:#94a3b8;font-size:11px;">${escapeHtml(
                item.product_id
              )} · ${item.quantity} × $${Number(item.unit_price).toFixed(2)}</div>
            </div>
            <div style="font-weight:700;">$${Number(item.line_total).toFixed(2)}</div>
          </div>`
        )
        .join("");

      els.cartSummaryBox.innerHTML = `
        ${lines}
        <div style="margin-top:10px;display:flex;flex-direction:column;gap:4px;">
          <div style="display:flex;justify-content:space-between;color:#94a3b8;">
            <span>Subtotal</span><span>$${Number(c.subtotal).toFixed(2)}</span>
          </div>
          ${
            c.promo_code
              ? `<div style="display:flex;justify-content:space-between;color:#34d399;">
                  <span>Promo (${escapeHtml(c.promo_code)})</span>
                  <span>-$${Number(c.discount).toFixed(2)}</span>
                </div>`
              : ""
          }
          <div style="display:flex;justify-content:space-between;color:#94a3b8;">
            <span>Shipping (${escapeHtml(c.delivery_speed || "standard")})</span>
            <span>$${Number(c.shipping_fee || 0).toFixed(2)}</span>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:15px;font-weight:800;margin-top:4px;padding-top:6px;border-top:1px solid #243049;">
            <span>Total</span><span style="color:#34d399;">$${Number(c.total).toFixed(2)}</span>
          </div>
        </div>
      `;
    }

    if (!state.orders || state.orders.length === 0) {
      els.ordersList.innerHTML =
        '<div style="color:#94a3b8;font-size:12px;">No orders placed yet.</div>';
    } else {
      els.ordersList.innerHTML = state.orders
        .slice()
        .reverse()
        .map(
          (o) => `
          <div class="order-banner">
            <div style="font-weight:800;color:#34d399;">Order ${escapeHtml(
              o.order_id
            )} Confirmed</div>
            <div>Recipient: ${escapeHtml(o.recipient)}</div>
            <div>Ship to: ${escapeHtml(o.shipping_address)}</div>
            <div style="margin-top:4px;font-weight:700;">Total Charged: $${Number(
              o.total_charged
            ).toFixed(2)}</div>
          </div>`
        )
        .join("");
    }
  }

  function renderShippingForm() {
    const s = state.shipping || {};
    if (s.full_name !== undefined) els.shippingForm.elements.full_name.value = s.full_name;
    if (s.email !== undefined) els.shippingForm.elements.email.value = s.email;
    if (s.address !== undefined) els.shippingForm.elements.address.value = s.address;
    if (s.delivery_speed) els.shippingForm.elements.delivery_speed.value = s.delivery_speed;
  }

  function renderSchemas(tools) {
    els.toolCountBadge.textContent = `${tools.length} WebMCP Tools`;
    els.registeredSchemasList.innerHTML = tools
      .map(
        (t) => `
        <div class="schema-card">
          <div class="schema-head">
            <span>${escapeHtml(t.name)}</span>
            <span class="src-badge ${escapeHtml(t.source)}">${escapeHtml(
          t.source
        )}</span>
          </div>
          <div style="color:#94a3b8;margin-bottom:6px;">${escapeHtml(
            t.description
          )}</div>
          <div style="font-family:monospace;font-size:10.5px;color:#cbd5e1;">
            API: ${escapeHtml(t.api)}
          </div>
        </div>`
      )
      .join("");
  }

  function prependRpcEvent(title, subtitle, badgeColor) {
    const first = els.rpcEventList.firstElementChild;
    if (first && first.textContent.includes("Waiting for WebMCP")) {
      els.rpcEventList.innerHTML = "";
    }
    const div = document.createElement("div");
    div.className = "event-card";
    div.style.borderLeft = `3px solid ${badgeColor || "#38bdf8"}`;
    div.innerHTML = `
      <div style="font-family:monospace;font-weight:700;font-size:11.5px;">${escapeHtml(
        title
      )}</div>
      <div style="font-family:monospace;font-size:11px;color:#94a3b8;margin-top:3px;word-break:break-all;">${escapeHtml(
        subtitle
      )}</div>
    `;
    els.rpcEventList.prepend(div);
  }

  function applySnapshot(snapshot) {
    if (!snapshot) return;
    if (snapshot.catalog) state.catalog = snapshot.catalog;
    if (snapshot.cart) state.cart = snapshot.cart;
    if (snapshot.shipping) state.shipping = snapshot.shipping;
    if (snapshot.active_filters) state.filters = snapshot.active_filters;
    if (snapshot.orders) state.orders = snapshot.orders;
    renderFilters();
    renderCatalog();
    renderCartAndOrders();
    renderShippingForm();
    if (snapshot.registered_tools) {
      renderSchemas(snapshot.registered_tools);
    }
  }

  /**
   * Register Imperative WebMCP Tools via navigator.modelContext.registerTool(...)
   */
  function registerImperativeWebMcpTools() {
    const mc =
      window.__webmcpContext ||
      window.navigator.modelContext ||
      document.modelContext;

    mc.registerTool({
      name: "search_products",
      description:
        "Search and filter the NexusGear storefront catalog by keyword, category (audio, peripherals, travel, monitors), maximum price, or stock availability.",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Keyword search query" },
          category: {
            type: "string",
            description: "Category filter (audio, peripherals, travel, monitors)",
          },
          max_price: {
            type: "number",
            description: "Maximum unit price in USD (0 for no limit)",
          },
          in_stock_only: {
            type: "boolean",
            description: "Whether to exclude out-of-stock products",
          },
        },
      },
      execute: async (args, meta) => {
        state.filters = {
          query: args.query || "",
          category: args.category || "",
          max_price: Number(args.max_price || 0),
          in_stock_only: Boolean(args.in_stock_only),
        };
        renderFilters();
        const res =
          (meta && meta.canonicalResult) || {
            status: "success",
            products: filteredProducts(),
          };
        const matchedIds = (res.products || []).map((p) => p.product_id || p.id);
        highlightProducts(matchedIds);
        showToast(`WebMCP search_products → ${matchedIds.length} match(es)`);
        return res;
      },
    });

    mc.registerTool({
      name: "get_product_details",
      description:
        "Retrieve complete technical specifications, stock count, and rating for a product by its product_id (e.g. prod-101).",
      inputSchema: {
        type: "object",
        properties: {
          product_id: { type: "string", description: "Product identifier" },
        },
        required: ["product_id"],
      },
      execute: async (args, meta) => {
        highlightProducts([args.product_id]);
        showToast(`WebMCP get_product_details(${args.product_id})`);
        return (meta && meta.canonicalResult) || { status: "success" };
      },
    });

    mc.registerTool({
      name: "add_to_cart",
      description: "Add a quantity of an in-stock product to the active shopping cart.",
      inputSchema: {
        type: "object",
        properties: {
          product_id: { type: "string", description: "Product identifier" },
          quantity: { type: "integer", description: "Quantity (1-10)" },
        },
        required: ["product_id", "quantity"],
      },
      execute: async (args, meta) => {
        highlightProducts([args.product_id]);
        showToast(`WebMCP add_to_cart → ${args.quantity}× ${args.product_id}`);
        return (meta && meta.canonicalResult) || { status: "success" };
      },
    });

    mc.registerTool({
      name: "remove_from_cart",
      description: "Remove a product completely from the active shopping cart.",
      inputSchema: {
        type: "object",
        properties: {
          product_id: { type: "string", description: "Product identifier" },
        },
        required: ["product_id"],
      },
      execute: async (args, meta) => {
        showToast(`WebMCP remove_from_cart(${args.product_id})`);
        return (meta && meta.canonicalResult) || { status: "success" };
      },
    });

    mc.registerTool({
      name: "get_cart",
      description:
        "Inspect the active shopping cart items, subtotal, applied promo discount, shipping details, and final total.",
      inputSchema: { type: "object", properties: {} },
      execute: async (_args, meta) => {
        showToast("WebMCP get_cart inspected");
        return (meta && meta.canonicalResult) || { status: "success", cart: state.cart };
      },
    });

    mc.registerTool({
      name: "apply_promo_code",
      description:
        "Apply a promotional discount code (e.g. WEBMCP20, ADK10, SAVE25).",
      inputSchema: {
        type: "object",
        properties: {
          code: { type: "string", description: "Promo code string" },
        },
        required: ["code"],
      },
      execute: async (args, meta) => {
        showToast(`WebMCP apply_promo_code(${args.code})`);
        return (meta && meta.canonicalResult) || { status: "success" };
      },
    });

    mc.registerTool({
      name: "checkout_order",
      description:
        "Submit and finalize purchase for the active shopping cart. Irreversible action — requires explicit user confirmation first.",
      inputSchema: {
        type: "object",
        properties: {
          full_name: { type: "string", description: "Recipient full name" },
          address: { type: "string", description: "Full shipping address" },
          user_confirmed: {
            type: "boolean",
            description: "True only after explicit user confirmation",
          },
        },
        required: ["full_name", "address", "user_confirmed"],
      },
      execute: async (args, meta) => {
        showToast(`Order placed for ${args.full_name}!`);
        return (meta && meta.canonicalResult) || { status: "success" };
      },
    });
  }

  /**
   * Embedded Google ADK Copilot Chat (/apps/app/... + /run_sse)
   */
  async function ensureAdkSession() {
    if (state.adkSessionId) return state.adkSessionId;
    const resp = await fetch(`/apps/app/users/${state.adkUserId}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state: { webmcp_session_id: "default" } }),
    });
    if (!resp.ok) {
      throw new Error(
        "ADK /apps/app endpoint not mounted on this port (run uvicorn app.fast_api_app:app --port 8000)."
      );
    }
    const data = await resp.json();
    state.adkSessionId = data.id;
    return state.adkSessionId;
  }

  function appendChatBubble(role, htmlOrText, isTool) {
    const div = document.createElement("div");
    if (isTool) {
      div.className = "tool-chip";
      div.textContent = htmlOrText;
    } else {
      div.className = `msg ${role}`;
      div.textContent = htmlOrText;
    }
    els.chatMessages.appendChild(div);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return div;
  }

  async function sendToAdkAgent(promptText) {
    if (!promptText.trim()) return;
    appendChatBubble("user", promptText, false);
    els.chatInput.value = "";

    let sessionId;
    try {
      sessionId = await ensureAdkSession();
    } catch (err) {
      appendChatBubble("agent", `Connection note: ${err.message}`, false);
      return;
    }

    const thinkingEl = appendChatBubble("agent", "Thinking...", false);

    try {
      const resp = await fetch("/run_sse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app_name: "app",
          user_id: state.adkUserId,
          session_id: sessionId,
          new_message: { role: "user", parts: [{ text: promptText }] },
          streaming: false,
        }),
      });

      if (!resp.ok) {
        const errTxt = await resp.text();
        thinkingEl.textContent = `ADK error (${resp.status}): ${errTxt.slice(0, 260)}`;
        return;
      }

      const raw = await resp.text();
      thinkingEl.remove();
      let finalReply = "";

      for (const line of raw.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        let evt;
        try {
          evt = JSON.parse(line.slice(6));
        } catch (_) {
          continue;
        }
        if (evt.error) {
          appendChatBubble("agent", `Error: ${evt.error}`, false);
          continue;
        }
        const parts = (evt.content && evt.content.parts) || [];
        for (const part of parts) {
          if (part.functionCall || part.function_call) {
            const fc = part.functionCall || part.function_call;
            appendChatBubble(
              "agent",
              `⚡ WebMCP Call → ${fc.name}(${JSON.stringify(fc.args || {})})`,
              true
            );
          }
          if (part.text) {
            finalReply = part.text;
          }
        }
      }

      if (finalReply) {
        appendChatBubble("agent", finalReply, false);
      }
      // Refresh UI state after turn
      const stResp = await fetch("/api/webmcp/state");
      if (stResp.ok) {
        applySnapshot(await stResp.json());
      }
    } catch (err) {
      thinkingEl.textContent = `Request failed: ${err.message}`;
    }
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Event Listeners
  window.addEventListener("webmcp:snapshot", (e) => applySnapshot(e.detail));

  window.addEventListener("webmcp:activity", (e) => {
    const d = e.detail || {};
    if (d.kind === "bridge_status") {
      els.bridgeDot.classList.toggle("online", Boolean(d.connected));
      els.bridgeStatusText.textContent = d.connected
        ? "WebMCP Bridge Live (WS)"
        : "Reconnecting Bridge...";
      if (d.tools) renderSchemas(d.tools);
    } else if (d.kind === "registry_updated" && d.tools) {
      renderSchemas(d.tools);
    } else if (d.kind === "tool_call_complete") {
      prependRpcEvent(
        `✓ ${d.tool} [${d.source || "imperative"}]`,
        `args: ${JSON.stringify(d.args)}`,
        "#34d399"
      );
    } else if (d.kind === "tool_call_error") {
      prependRpcEvent(`✕ ${d.tool}`, JSON.stringify(d.result), "#fb7185");
    }
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".tab-btn")
        .forEach((b) => b.classList.remove("active"));
      document
        .querySelectorAll(".tab-panel")
        .forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
    });
  });

  els.searchInput.addEventListener("input", () => {
    state.filters.query = els.searchInput.value;
    renderCatalog();
  });

  els.categoryPills.querySelectorAll(".cat-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.filters.category = btn.dataset.cat || "";
      renderFilters();
      renderCatalog();
    });
  });

  els.maxPriceInput.addEventListener("input", () => {
    state.filters.max_price = Number(els.maxPriceInput.value || 0);
    renderCatalog();
  });

  els.inStockCheckbox.addEventListener("change", () => {
    state.filters.in_stock_only = els.inStockCheckbox.checked;
    renderCatalog();
  });

  els.toggleMarkupBtn.addEventListener("click", () => {
    els.markupPreview.classList.toggle("open");
  });

  els.shippingForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(els.shippingForm);
    await fetch("/api/webmcp/call", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: "update_shipping_form",
        args: {
          full_name: fd.get("full_name") || "",
          email: fd.get("email") || "",
          address: fd.get("address") || "",
          delivery_speed: fd.get("delivery_speed") || "standard",
        },
      }),
    });
    showToast("Shipping details saved");
  });

  els.applyPromoBtn.addEventListener("click", async () => {
    const code = els.manualPromoInput.value.trim();
    if (!code) return;
    await fetch("/api/webmcp/call", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: "apply_promo_code",
        args: { code },
      }),
    });
  });

  els.resetBtn.addEventListener("click", async () => {
    state.adkSessionId = null;
    await fetch("/api/webmcp/reset", { method: "POST" });
    showToast("Demo storefront & cart reset");
  });

  els.chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendToAdkAgent(els.chatInput.value);
  });

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      sendToAdkAgent(chip.dataset.prompt || "");
    });
  });

  // Boot Imperative tools & fetch initial snapshot
  registerImperativeWebMcpTools();
  fetch("/api/webmcp/state")
    .then((r) => r.json())
    .then((snap) => applySnapshot(snap))
    .catch(() => {});
})();

