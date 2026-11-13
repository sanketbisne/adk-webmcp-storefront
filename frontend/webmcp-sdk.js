/**
 * WebMCP Browser SDK & Polyfill (navigator.modelContext)
 *
 * Implements the W3C / Chrome Web Model Context Protocol (WebMCP) surface:
 *  1. Imperative API: navigator.modelContext.registerTool / unregisterTool / provideContext / clearContext
 *  2. Declarative API: Automatic discovery of <form toolname="..." tooldescription="..."> elements
 *  3. Live WebSocket relay to the Google ADK WebMCP Bridge (/ws/webmcp)
 */
(function () {
  "use strict";

  const nativeContext =
    typeof navigator !== "undefined" && navigator.modelContext
      ? navigator.modelContext
      : null;

  const toolRegistry = new Map();
  let ws = null;
  let wsConnected = false;
  let reconnectTimer = null;

  function emitActivity(detail) {
    window.dispatchEvent(new CustomEvent("webmcp:activity", { detail }));
  }

  function serializeTools() {
    return Array.from(toolRegistry.values()).map((entry) => ({
      name: entry.name,
      source: entry.source || "imperative",
      api:
        entry.source === "declarative"
          ? `HTML <form toolname="${entry.name}">`
          : "navigator.modelContext.registerTool",
      description: entry.description || "",
      inputSchema: entry.inputSchema || { type: "object", properties: {} },
      annotations: entry.annotations || {},
    }));
  }

  function pushToolsToBridge() {
    const tools = serializeTools();
    emitActivity({
      kind: "registry_updated",
      tools,
      connected: wsConnected,
    });
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "webmcp:register_tools",
          tools,
        })
      );
    }
  }

  const modelContextShim = {
    isNativeBacked: Boolean(nativeContext),

    registerTool(toolDef) {
      if (!toolDef || !toolDef.name || typeof toolDef.execute !== "function") {
        throw new TypeError(
          "navigator.modelContext.registerTool requires { name, description, inputSchema, execute }"
        );
      }
      toolRegistry.set(toolDef.name, {
        name: toolDef.name,
        source: toolDef._declarative ? "declarative" : "imperative",
        description: toolDef.description || "",
        inputSchema: toolDef.inputSchema || { type: "object", properties: {} },
        annotations: toolDef.annotations || {},
        execute: toolDef.execute,
      });

      if (nativeContext && typeof nativeContext.registerTool === "function") {
        try {
          nativeContext.registerTool(toolDef);
        } catch (_) {
          // Ignore duplicate registration on native experimental surface
        }
      }

      pushToolsToBridge();
      return () => this.unregisterTool(toolDef.name);
    },

    unregisterTool(name) {
      toolRegistry.delete(name);
      if (nativeContext && typeof nativeContext.unregisterTool === "function") {
        try {
          nativeContext.unregisterTool(name);
        } catch (_) {}
      }
      pushToolsToBridge();
    },

    provideContext(contextObj) {
      toolRegistry.clear();
      const tools = (contextObj && contextObj.tools) || [];
      for (const tool of tools) {
        this.registerTool(tool);
      }
    },

    clearContext() {
      toolRegistry.clear();
      if (nativeContext && typeof nativeContext.clearContext === "function") {
        try {
          nativeContext.clearContext();
        } catch (_) {}
      }
      pushToolsToBridge();
    },

    getRegisteredTools() {
      return serializeTools();
    },

    async invokeLocalTool(name, args, meta) {
      const entry = toolRegistry.get(name);
      if (!entry) {
        return {
          status: "error",
          error: `WebMCP tool '${name}' is not registered on this page.`,
        };
      }
      emitActivity({
        kind: "tool_call_start",
        tool: name,
        source: entry.source,
        args: args || {},
      });
      try {
        const result = await entry.execute(args || {}, meta || {});
        emitActivity({
          kind: "tool_call_complete",
          tool: name,
          source: entry.source,
          args: args || {},
          result,
        });
        return result;
      } catch (err) {
        const errPayload = {
          status: "error",
          error: err && err.message ? err.message : String(err),
        };
        emitActivity({
          kind: "tool_call_error",
          tool: name,
          args: args || {},
          result: errPayload,
        });
        return errPayload;
      }
    },

    syncStateToBridge(statePayload) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: "webmcp:sync_state",
            state: statePayload,
          })
        );
      }
    },
  };

  Object.defineProperty(window.navigator, "modelContext", {
    value: modelContextShim,
    configurable: true,
    enumerable: true,
  });

  /**
   * Declarative WebMCP HTML Form Scanner
   * Synthesizes JSON Schema & tool executor from <form toolname="..." tooldescription="...">
   */
  function extractFormSchema(formEl) {
    const properties = {};
    const required = [];
    const controls = formEl.querySelectorAll("input[name], select[name], textarea[name]");

    controls.forEach((ctrl) => {
      const name = ctrl.getAttribute("name");
      if (!name) return;

      const paramDesc =
        ctrl.getAttribute("toolparamdescription") ||
        ctrl.getAttribute("placeholder") ||
        name;

      let propSchema = { type: "string", description: paramDesc };

      if (ctrl.tagName === "SELECT") {
        const options = Array.from(ctrl.options)
          .map((o) => o.value)
          .filter(Boolean);
        if (options.length > 0) {
          propSchema.enum = options;
        }
      } else if (ctrl.type === "number" || ctrl.type === "range") {
        propSchema.type = "number";
      } else if (ctrl.type === "checkbox") {
        propSchema.type = "boolean";
      }

      properties[name] = propSchema;
      if (ctrl.required) {
        required.push(name);
      }
    });

    const schema = { type: "object", properties };
    if (required.length > 0) {
      schema.required = required;
    }
    return schema;
  }

  function scanDeclarativeForms() {
    const forms = document.querySelectorAll("form[toolname]");
    forms.forEach((formEl) => {
      const toolName = formEl.getAttribute("toolname");
      if (!toolName || formEl.dataset.webmcpBound === "true") return;

      formEl.dataset.webmcpBound = "true";
      const description =
        formEl.getAttribute("tooldescription") ||
        `Declarative HTML form tool (${toolName})`;
      const inputSchema = extractFormSchema(formEl);

      window.navigator.modelContext.registerTool({
        name: toolName,
        description,
        inputSchema,
        _declarative: true,
        execute: async (args, meta) => {
          formEl.classList.add("webmcp-actuated");
          setTimeout(() => formEl.classList.remove("webmcp-actuated"), 1800);

          Object.entries(args || {}).forEach(([key, val]) => {
            const field = formEl.elements.namedItem(key);
            if (!field) return;
            if (field.type === "checkbox") {
              field.checked = Boolean(val);
            } else {
              field.value = String(val);
            }
            field.classList.add("field-flash");
            setTimeout(() => field.classList.remove("field-flash"), 1400);
            field.dispatchEvent(new Event("input", { bubbles: true }));
            field.dispatchEvent(new Event("change", { bubbles: true }));
          });

          formEl.dispatchEvent(
            new CustomEvent("webmcp:declarative-submit", {
              bubbles: true,
              detail: { args, meta },
            })
          );

          if (meta && meta.canonicalResult) {
            return meta.canonicalResult;
          }
          return {
            status: "success",
            webmcp_source: "declarative_form",
            populated_fields: args,
          };
        },
      });
    });
  }

  function connectBridge() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/webmcp`;

    try {
      ws = new WebSocket(wsUrl);
    } catch (_) {
      reconnectTimer = setTimeout(connectBridge, 3000);
      return;
    }

    ws.addEventListener("open", () => {
      wsConnected = true;
      emitActivity({
        kind: "bridge_status",
        connected: true,
        tools: serializeTools(),
      });
      pushToolsToBridge();
    });

    ws.addEventListener("message", async (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (_) {
        return;
      }

      if (msg.type === "webmcp:init" || msg.type === "webmcp:state_sync") {
        window.dispatchEvent(
          new CustomEvent("webmcp:snapshot", { detail: msg.snapshot })
        );
      } else if (msg.type === "webmcp:call_tool") {
        const result = await window.navigator.modelContext.invokeLocalTool(
          msg.tool,
          msg.args,
          {
            callId: msg.callId,
            canonicalResult: msg.canonicalResult,
            snapshot: msg.snapshot,
          }
        );
        if (msg.snapshot) {
          window.dispatchEvent(
            new CustomEvent("webmcp:snapshot", { detail: msg.snapshot })
          );
        }
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(
            JSON.stringify({
              type: "webmcp:tool_result",
              callId: msg.callId,
              result,
            })
          );
        }
      }
    });

    ws.addEventListener("close", () => {
      wsConnected = false;
      emitActivity({
        kind: "bridge_status",
        connected: false,
        tools: serializeTools(),
      });
      reconnectTimer = setTimeout(connectBridge, 2500);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      scanDeclarativeForms();
      connectBridge();
    });
  } else {
    scanDeclarativeForms();
    connectBridge();
  }

  const observer = new MutationObserver(() => scanDeclarativeForms());
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();

