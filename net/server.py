"""
net/server.py — WebSocket + HTTP server that hosts a player view for D&D VTT.

Serves a single-page HTML player view with a Canvas that renders the map,
grid overlay, and visible tokens in real time. WebSocket pushes game state
updates; DM-only information (hidden tokens, monster HP/AC) is filtered out.

Dependencies: websockets, qrcode, Pillow (already in project deps).
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import socket
import tempfile
import threading
from functools import partial
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional, Set

try:
    import websockets
    import websockets.asyncio.server
    import websockets.http11
    import websockets.datastructures
    import websockets.exceptions
except ImportError:
    websockets = None  # type: ignore[assignment]

try:
    import qrcode
except ImportError:
    qrcode = None  # type: ignore[assignment]

# Avoid circular imports — only type-check against game_state
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.game_state import EncounterState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LAN IP detection
# ---------------------------------------------------------------------------

def _get_lan_ip() -> str:
    """Best-effort LAN IP detection. Falls back to 0.0.0.0."""
    # Method 1: connect a UDP socket to a public address (no traffic sent)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # Method 2: gethostbyname
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # Method 3: iterate network interfaces (Linux /proc shortcut)
    try:
        import subprocess
        result = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, timeout=2
        )
        for part in result.stdout.strip().split():
            if "." in part and not part.startswith("127."):
                return part
    except Exception:
        pass

    return "0.0.0.0"


# ---------------------------------------------------------------------------
# Player HTML page (served as a string)
# ---------------------------------------------------------------------------

PLAYER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes">
<title>D&D Player View</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: #1a1a2e; }
  canvas { display: block; touch-action: none; }
  #status {
    position: fixed; top: 8px; left: 8px; z-index: 10;
    font: 600 13px/1.3 system-ui, sans-serif;
    color: #e0e0e0; background: rgba(26,26,46,0.85);
    padding: 4px 10px; border-radius: 6px;
    pointer-events: none; transition: opacity 0.3s;
  }
  #status.connected { color: #4ade80; }
  #status.disconnected { color: #f87171; }
  #round-info {
    position: fixed; top: 8px; right: 8px; z-index: 10;
    font: 600 14px/1.3 system-ui, sans-serif;
    color: #fbbf24; background: rgba(26,26,46,0.85);
    padding: 4px 10px; border-radius: 6px;
    pointer-events: none;
  }
</style>
</head>
<body>
<div id="status" class="disconnected">Connecting...</div>
<div id="round-info"></div>
<canvas id="board"></canvas>

<script>
"use strict";

// ---- State ----
let state = null;
let mapImg = null;
let mapLoaded = false;
let tokenImages = {};  // id -> Image
let ws = null;
let reconnectTimer = null;

const canvas = document.getElementById("board");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");
const roundEl = document.getElementById("round-info");

// ---- Canvas sizing ----
function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  render();
}
window.addEventListener("resize", resize);
resize();

// ---- Pan & Zoom + Token Dragging (mouse + touch) ----
let camX = 0, camY = 0, camZoom = 1;
let dragging = false, dragStartX = 0, dragStartY = 0, camStartX = 0, camStartY = 0;
let pinchDist0 = null, pinchZoom0 = 1;

// Token dragging state
let dragToken = null;       // creature being dragged (or null for pan)
let dragTokenGX = 0, dragTokenGY = 0;  // current grid pos while dragging

function screenToMap(sx, sy) {
  // Convert screen coords to map coords (pixels in map space)
  return { x: (sx - camX) / camZoom, y: (sy - camY) / camZoom };
}

function hitTestToken(sx, sy) {
  // Returns the first player creature under screen coords, or null
  if (!state) return null;
  var mp = screenToMap(sx, sy);
  var mapW = state.map_width_px || (mapImg ? mapImg.naturalWidth : 800);
  var mapH = state.map_height_px || (mapImg ? mapImg.naturalHeight : 600);
  var gridW = state.map_width_sq || 30;
  var gridH = state.map_height_sq || 20;
  // Square cells based on width — matches DM view
  var cellW = mapW / gridW;
  var cellH = cellW;
  var creatures = state.creatures || [];
  // Check in reverse order (topmost first)
  for (var i = creatures.length - 1; i >= 0; i--) {
    var c = creatures[i];
    if (!c.is_player) continue;
    var cx = (c.position[0] + 0.5) * cellW;
    var cy = (c.position[1] + 0.5) * cellH;
    var radius = cellW * 0.42 * (c.token_scale || 1.0);
    var dx = mp.x - cx, dy = mp.y - cy;
    if (dx * dx + dy * dy <= radius * radius) return c;
  }
  return null;
}

canvas.addEventListener("mousedown", function(e) {
  var token = hitTestToken(e.clientX, e.clientY);
  if (token) {
    dragToken = token;
    dragTokenGX = token.position[0];
    dragTokenGY = token.position[1];
    canvas.style.cursor = "grabbing";
  } else {
    dragging = true; dragStartX = e.clientX; dragStartY = e.clientY;
    camStartX = camX; camStartY = camY;
  }
});
canvas.addEventListener("mousemove", function(e) {
  if (dragToken) {
    // Move the dragged token to follow cursor
    var mp = screenToMap(e.clientX, e.clientY);
    var mapW = state.map_width_px || (mapImg ? mapImg.naturalWidth : 800);
    var gridW = state.map_width_sq || 30;
    var cellW = mapW / gridW;
    var cellH = cellW;
    dragTokenGX = mp.x / cellW - 0.5;
    dragTokenGY = mp.y / cellH - 0.5;
    // Temporarily update creature position for rendering
    dragToken.position = [dragTokenGX, dragTokenGY];
    render();
    return;
  }
  if (!dragging) {
    // Show grab cursor when hovering over player tokens
    var token = hitTestToken(e.clientX, e.clientY);
    canvas.style.cursor = token ? "grab" : "default";
    return;
  }
  camX = camStartX + (e.clientX - dragStartX);
  camY = camStartY + (e.clientY - dragStartY);
  render();
});
canvas.addEventListener("mouseup", function(e) {
  if (dragToken) {
    // Snap to grid and send move to server
    var gx = Math.round(dragTokenGX);
    var gy = Math.round(dragTokenGY);
    dragToken.position = [gx, gy];
    sendTokenMove(dragToken.id, gx, gy);
    dragToken = null;
    canvas.style.cursor = "default";
    render();
    return;
  }
  dragging = false;
});
canvas.addEventListener("mouseleave", function() {
  if (dragToken) {
    var gx = Math.round(dragTokenGX);
    var gy = Math.round(dragTokenGY);
    dragToken.position = [gx, gy];
    sendTokenMove(dragToken.id, gx, gy);
    dragToken = null;
    canvas.style.cursor = "default";
    render();
  }
  dragging = false;
});
canvas.addEventListener("wheel", function(e) {
  e.preventDefault();
  var factor = e.deltaY < 0 ? 1.1 : 0.9;
  var mx = e.clientX, my = e.clientY;
  camX = mx - (mx - camX) * factor;
  camY = my - (my - camY) * factor;
  camZoom *= factor;
  camZoom = Math.max(0.1, Math.min(camZoom, 10));
  render();
}, { passive: false });

// Touch: pan, pinch zoom, and token dragging
canvas.addEventListener("touchstart", function(e) {
  if (e.touches.length === 1) {
    var token = hitTestToken(e.touches[0].clientX, e.touches[0].clientY);
    if (token) {
      dragToken = token;
      dragTokenGX = token.position[0];
      dragTokenGY = token.position[1];
    } else {
      dragging = true;
      dragStartX = e.touches[0].clientX; dragStartY = e.touches[0].clientY;
      camStartX = camX; camStartY = camY;
    }
  } else if (e.touches.length === 2) {
    dragging = false; dragToken = null;
    var dx = e.touches[1].clientX - e.touches[0].clientX;
    var dy = e.touches[1].clientY - e.touches[0].clientY;
    pinchDist0 = Math.hypot(dx, dy);
    pinchZoom0 = camZoom;
  }
}, { passive: true });
canvas.addEventListener("touchmove", function(e) {
  e.preventDefault();
  if (e.touches.length === 1 && dragToken) {
    var mp = screenToMap(e.touches[0].clientX, e.touches[0].clientY);
    var mapW = state.map_width_px || (mapImg ? mapImg.naturalWidth : 800);
    var gridW = state.map_width_sq || 30;
    var cellW = mapW / gridW;
    var cellH = cellW;
    dragTokenGX = mp.x / cellW - 0.5;
    dragTokenGY = mp.y / cellH - 0.5;
    dragToken.position = [dragTokenGX, dragTokenGY];
    render();
  } else if (e.touches.length === 1 && dragging) {
    camX = camStartX + (e.touches[0].clientX - dragStartX);
    camY = camStartY + (e.touches[0].clientY - dragStartY);
    render();
  } else if (e.touches.length === 2 && pinchDist0) {
    var dx = e.touches[1].clientX - e.touches[0].clientX;
    var dy = e.touches[1].clientY - e.touches[0].clientY;
    var dist = Math.hypot(dx, dy);
    camZoom = Math.max(0.1, Math.min(pinchZoom0 * (dist / pinchDist0), 10));
    render();
  }
}, { passive: false });
canvas.addEventListener("touchend", function() {
  if (dragToken) {
    var gx = Math.round(dragTokenGX);
    var gy = Math.round(dragTokenGY);
    dragToken.position = [gx, gy];
    sendTokenMove(dragToken.id, gx, gy);
    dragToken = null;
    render();
  }
  dragging = false; pinchDist0 = null;
});

function sendTokenMove(creatureId, gx, gy) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "token_move", id: creatureId, gx: gx, gy: gy }));
  }
}

// ---- Map image loading ----
function loadMap() {
  mapImg = new Image();
  mapImg.onload = function() { mapLoaded = true; fitMap(); render(); };
  mapImg.onerror = function() { mapLoaded = false; };
  mapImg.src = "/map?" + Date.now();
}

function fitMap() {
  if (!mapImg || !mapLoaded || !state) return;
  var pad = 20;
  var scaleX = (canvas.width - pad * 2) / mapImg.naturalWidth;
  var scaleY = (canvas.height - pad * 2) / mapImg.naturalHeight;
  camZoom = Math.min(scaleX, scaleY, 1.5);
  camX = (canvas.width - mapImg.naturalWidth * camZoom) / 2;
  camY = (canvas.height - mapImg.naturalHeight * camZoom) / 2;
}

// ---- Token image cache ----
function ensureTokenImage(creature) {
  if (!creature.token_url) return null;
  if (tokenImages[creature.id] && tokenImages[creature.id]._src === creature.token_url) {
    return tokenImages[creature.id].complete ? tokenImages[creature.id] : null;
  }
  var img = new Image();
  img._src = creature.token_url;
  img.onload = function() { render(); };
  img.src = creature.token_url;
  tokenImages[creature.id] = img;
  return img.complete ? img : null;
}

// ---- Rendering ----
function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#1a1a2e";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (!state) {
    ctx.fillStyle = "#7c7c9e";
    ctx.font = "20px system-ui";
    ctx.textAlign = "center";
    ctx.fillText("Waiting for encounter data...", canvas.width / 2, canvas.height / 2);
    return;
  }

  ctx.save();
  ctx.translate(camX, camY);
  ctx.scale(camZoom, camZoom);

  var mapW = state.map_width_px || (mapImg ? mapImg.naturalWidth : 800);
  var mapH = state.map_height_px || (mapImg ? mapImg.naturalHeight : 600);
  var gridW = state.map_width_sq || 30;
  var gridH = state.map_height_sq || 20;
  // Square cells based on width — matches DM view
  var cellW = mapW / gridW;
  var cellH = cellW;

  // Map background
  if (mapLoaded && mapImg) {
    ctx.drawImage(mapImg, 0, 0, mapW, mapH);
  } else {
    ctx.fillStyle = "#2a2a3e";
    ctx.fillRect(0, 0, mapW, mapH);
  }

  // Grid overlay
  ctx.strokeStyle = "rgba(255,255,255,0.12)";
  ctx.lineWidth = 1;
  for (var x = 0; x <= gridW; x++) {
    ctx.beginPath();
    ctx.moveTo(x * cellW, 0);
    ctx.lineTo(x * cellW, mapH);
    ctx.stroke();
  }
  for (var y = 0; y * cellH <= mapH + 0.1; y++) {
    ctx.beginPath();
    ctx.moveTo(0, y * cellH);
    ctx.lineTo(mapW, y * cellH);
    ctx.stroke();
  }

  // Draw tokens
  var creatures = state.creatures || [];
  for (var i = 0; i < creatures.length; i++) {
    var c = creatures[i];
    var gx = c.position[0];
    var gy = c.position[1];
    var cx = (gx + 0.5) * cellW;
    var cy = (gy + 0.5) * cellH;
    var radius = cellW * 0.42 * (c.token_scale || 1.0);

    var isActive = state.active_creature_id && c.id === state.active_creature_id;

    ctx.save();

    // Glow for active creature
    if (isActive) {
      ctx.shadowColor = "#fbbf24";
      ctx.shadowBlur = 18;
    }

    // Draw token image or colored circle
    var tImg = ensureTokenImage(c);
    if (tImg) {
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.closePath();
      ctx.clip();
      ctx.drawImage(tImg, cx - radius, cy - radius, radius * 2, radius * 2);
      ctx.restore();
      ctx.save();
      // Border
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = c.is_player ? "#4ade80" : "#f87171";
      if (isActive) { ctx.strokeStyle = "#fbbf24"; ctx.lineWidth = 3.5; }
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fillStyle = c.is_player ? "rgba(74,222,128,0.45)" : "rgba(248,113,113,0.45)";
      ctx.fill();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = c.is_player ? "#4ade80" : "#f87171";
      if (isActive) { ctx.strokeStyle = "#fbbf24"; ctx.lineWidth = 3.5; }
      ctx.stroke();
    }

    ctx.restore();

    // Conditions badge
    if (c.conditions && c.conditions.length > 0) {
      ctx.save();
      ctx.font = "bold " + Math.max(10, cellW * 0.15) + "px system-ui";
      ctx.fillStyle = "#fbbf24";
      ctx.textAlign = "center";
      ctx.fillText(c.conditions.join(", "), cx, cy + radius + cellH * 0.22);
      ctx.restore();
    }

    // Name label
    ctx.save();
    var fontSize = Math.max(11, cellW * 0.22);
    ctx.font = "600 " + fontSize + "px system-ui";
    ctx.textAlign = "center";
    ctx.fillStyle = "#fff";
    ctx.shadowColor = "rgba(0,0,0,0.7)";
    ctx.shadowBlur = 3;
    ctx.fillText(c.name, cx, cy - radius - 6);
    ctx.restore();

    // HP bar (only for player creatures — monsters never show HP to players)
    if (c.is_player && typeof c.hp === "number" && typeof c.hp_max === "number" && c.hp_max > 0) {
      var barW = radius * 1.8;
      var barH = Math.max(4, cellW * 0.07);
      var barX = cx - barW / 2;
      var barY = cy + radius + 3;
      var hpFrac = Math.max(0, Math.min(c.hp / c.hp_max, 1));

      // Background
      ctx.fillStyle = "rgba(0,0,0,0.5)";
      ctx.fillRect(barX, barY, barW, barH);

      // Fill
      var barColor = "#4ade80";
      if (hpFrac < 0.5) barColor = "#fbbf24";
      if (hpFrac < 0.25) barColor = "#f87171";
      ctx.fillStyle = barColor;
      ctx.fillRect(barX, barY, barW * hpFrac, barH);

      // Border
      ctx.strokeStyle = "rgba(255,255,255,0.3)";
      ctx.lineWidth = 1;
      ctx.strokeRect(barX, barY, barW, barH);

      // HP text
      ctx.save();
      ctx.font = "600 " + Math.max(9, cellW * 0.14) + "px system-ui";
      ctx.fillStyle = "#fff";
      ctx.textAlign = "center";
      ctx.shadowColor = "rgba(0,0,0,0.8)";
      ctx.shadowBlur = 2;
      var hpText = c.hp_temp > 0 ? c.hp + "+" + c.hp_temp + "/" + c.hp_max : c.hp + "/" + c.hp_max;
      ctx.fillText(hpText, cx, barY + barH + fontSize * 0.7);
      ctx.restore();
    }
  }

  ctx.restore();

  // Round info
  if (state.combat_started) {
    roundEl.textContent = "Round " + (state.round_number || 1);
    roundEl.style.display = "";
  } else {
    roundEl.style.display = "none";
  }
}

// ---- WebSocket ----
function connectWS() {
  var proto = location.protocol === "https:" ? "wss:" : "ws:";
  var url = proto + "//" + location.host + "/ws";
  ws = new WebSocket(url);

  ws.onopen = function() {
    statusEl.textContent = "Connected";
    statusEl.className = "connected";
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  };

  ws.onmessage = function(evt) {
    try {
      var msg = JSON.parse(evt.data);
      if (msg.type === "state") {
        var needsMapReload = !state || msg.map_changed;
        state = msg;
        if (needsMapReload) { loadMap(); }
        render();
      } else if (msg.type === "map_changed") {
        loadMap();
      }
    } catch (e) { console.error("WS parse error:", e); }
  };

  ws.onclose = function() {
    statusEl.textContent = "Disconnected \u2014 reconnecting...";
    statusEl.className = "disconnected";
    scheduleReconnect();
  };

  ws.onerror = function() {
    ws.close();
  };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(function() {
    reconnectTimer = null;
    connectWS();
  }, 2000);
}

// ---- Init ----
connectWS();
loadMap();

</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP Request Handler (fallback for non-websockets setups)
# ---------------------------------------------------------------------------

class _PlayerHTTPHandler(BaseHTTPRequestHandler):
    """Serves the player HTML page and the map image."""

    server_ref: "PlayerViewServer"  # injected via partial

    def __init__(self, server_ref: "PlayerViewServer", *args, **kwargs):
        self.server_ref = server_ref
        super().__init__(*args, **kwargs)

    def log_message(self, fmt, *args):
        logger.debug("HTTP %s", fmt % args)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            self._serve_html()
        elif path == "/map":
            self._serve_map()
        elif path.startswith("/token/"):
            self._serve_token(path)
        else:
            self.send_error(404, "Not Found")

    def _serve_html(self):
        body = PLAYER_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _serve_map(self):
        map_path = self.server_ref._map_path
        if not map_path or not os.path.isfile(map_path):
            self.send_response(204)
            self.end_headers()
            return

        mime, _ = mimetypes.guess_type(map_path)
        if not mime:
            mime = "image/jpeg"

        try:
            with open(map_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            logger.warning("Failed to serve map: %s", e)
            self.send_error(500, "Map read error")

    def _serve_token(self, path: str):
        """Serve a token image by creature id: /token/<creature_id>"""
        creature_id = path.split("/token/", 1)[-1]
        enc = self.server_ref._encounter
        if not enc:
            self.send_error(404, "No encounter")
            return

        creature = None
        for c in enc.creatures:
            if c.id == creature_id:
                creature = c
                break

        if not creature or not creature.token_path or not os.path.isfile(creature.token_path):
            self.send_error(404, "Token not found")
            return

        mime, _ = mimetypes.guess_type(creature.token_path)
        if not mime:
            mime = "image/png"

        try:
            with open(creature.token_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=300")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            logger.warning("Failed to serve token image: %s", e)
            self.send_error(500, "Token read error")


# ---------------------------------------------------------------------------
# PlayerViewServer
# ---------------------------------------------------------------------------

class PlayerViewServer:
    """
    Combined HTTP + WebSocket server that streams a filtered player view
    of the current D&D encounter.

    Usage::

        server = PlayerViewServer(port=8080)
        server.set_encounter(encounter, map_path, 30, 20)
        server.start()
        # ... game runs, call broadcast_state() after each change ...
        server.stop()
    """

    def __init__(self, port: int = 8080, on_token_moved=None):
        self.port = port
        self._encounter: Optional[Any] = None  # EncounterState
        self._map_path: Optional[str] = None
        self._map_width: int = 0
        self._map_height: int = 0
        self._ws_clients: Set = set()
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._http_server: Optional[HTTPServer] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lan_ip: str = _get_lan_ip()
        self._map_image_width: int = 0
        self._map_image_height: int = 0
        self._lock = threading.Lock()
        self._qr_path: Optional[str] = None
        self._on_token_moved = on_token_moved  # callback(creature_id, gx, gy)

    # -- Public API --------------------------------------------------------

    def set_encounter(
        self,
        encounter: "EncounterState",
        map_path: str,
        width_sq: int,
        height_sq: int,
    ) -> None:
        """Set current game state. Thread-safe — called from the main/Qt thread."""
        with self._lock:
            self._encounter = encounter
            self._map_path = map_path
            self._map_width = width_sq
            self._map_height = height_sq
            # Probe actual pixel dimensions for the canvas
            self._map_image_width = 0
            self._map_image_height = 0
            if map_path and os.path.isfile(map_path):
                try:
                    from PIL import Image
                    with Image.open(map_path) as img:
                        self._map_image_width, self._map_image_height = img.size
                except Exception:
                    pass

    def start(self) -> None:
        """Start HTTP + WebSocket servers in a background daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="PlayerViewServer"
        )
        self._thread.start()
        logger.info("PlayerViewServer starting on port %d", self.port)

    def stop(self) -> None:
        """Stop both servers and join the background thread."""
        self._running = False

        # Shut down HTTP server (if using fallback mode)
        if self._http_server:
            try:
                self._http_server.shutdown()
            except Exception:
                pass

        # Shut down asyncio event loop — the _ws_main coroutine checks
        # self._running and will clean up the socket before exiting.
        # We just need to wait for the thread to finish.
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._thread = None
        self._loop = None

        # Clean up QR temp file
        if self._qr_path and os.path.exists(self._qr_path):
            try:
                os.unlink(self._qr_path)
            except Exception:
                pass
            self._qr_path = None

        print("[PlayerView] Server stopped")

    def broadcast_state(self) -> None:
        """Send current state to all connected WebSocket clients."""
        if not self._loop or not self._running:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._async_broadcast(), self._loop)
        except RuntimeError:
            # Loop already closed
            pass

    def get_player_state(self) -> Dict[str, Any]:
        """
        Build a player-safe snapshot of the encounter state.

        Filtering rules:
        - Creatures with is_visible=False are excluded entirely.
        - Non-player creatures (monsters/NPCs): hp, hp_max, hp_temp, ac,
          speed, notes, death_saves, initiative_modifier are stripped.
        - Player creatures keep full stat info.
        - Map dimensions and combat metadata are always included.
        """
        with self._lock:
            enc = self._encounter
            map_w = self._map_width
            map_h = self._map_height
            img_w = self._map_image_width
            img_h = self._map_image_height

        result: Dict[str, Any] = {
            "type": "state",
            "map_width_sq": map_w,
            "map_height_sq": map_h,
            "map_width_px": img_w,
            "map_height_px": img_h,
            "creatures": [],
            "combat_started": False,
            "round_number": 0,
            "active_creature_id": None,
            "map_changed": False,
        }

        if enc is None:
            return result

        result["combat_started"] = enc.combat_started
        result["round_number"] = enc.round_number

        active = enc.get_active_creature()
        if active and active.is_visible:
            result["active_creature_id"] = active.id

        for creature in enc.creatures:
            if not creature.is_visible:
                continue

            if creature.is_player:
                # Full info for player characters
                c_data: Dict[str, Any] = {
                    "id": creature.id,
                    "name": creature.name,
                    "hp": creature.hp,
                    "hp_max": creature.hp_max,
                    "hp_temp": creature.hp_temp,
                    "ac": creature.ac,
                    "is_player": True,
                    "position": list(creature.position),
                    "token_scale": creature.token_scale,
                    "size_category": creature.size_category,
                    "conditions": list(creature.conditions),
                    "token_url": f"/token/{creature.id}" if creature.token_path else "",
                }
            else:
                # Monsters/NPCs: hide combat stats entirely
                c_data = {
                    "id": creature.id,
                    "name": creature.name,
                    "is_player": False,
                    "position": list(creature.position),
                    "token_scale": creature.token_scale,
                    "size_category": creature.size_category,
                    "conditions": list(creature.conditions),
                    "token_url": f"/token/{creature.id}" if creature.token_path else "",
                }

            result["creatures"].append(c_data)

        return result

    def get_url(self) -> str:
        """Return the URL players should connect to."""
        ip = self._lan_ip if self._lan_ip != "0.0.0.0" else "localhost"
        return f"http://{ip}:{self.port}/"

    def get_qr_code_path(self) -> str:
        """
        Generate a QR code PNG for the player URL, save to a temp file,
        and return the path. Returns empty string if qrcode is not installed.
        """
        if qrcode is None:
            logger.warning("qrcode library not installed — cannot generate QR code")
            return ""

        url = self.get_url()

        # Reuse existing file if URL hasn't changed
        if self._qr_path and os.path.exists(self._qr_path):
            return self._qr_path

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#e0e0e0", back_color="#1a1a2e")

            fd, path = tempfile.mkstemp(suffix=".png", prefix="dnd_qr_")
            os.close(fd)
            img.save(path)
            self._qr_path = path
            return path
        except Exception as e:
            logger.warning("QR generation failed: %s", e)
            return ""

    def _handle_player_token_move(self, msg: dict) -> None:
        """Process a token_move message from a player client."""
        creature_id = msg.get("id")
        gx = msg.get("gx")
        gy = msg.get("gy")
        if creature_id is None or gx is None or gy is None:
            logger.info("token_move: missing fields in %s", msg)
            return

        with self._lock:
            enc = self._encounter
        if not enc:
            logger.info("token_move: no encounter set")
            return

        # Only allow moving player characters
        creature = enc.get_creature(creature_id)
        if not creature:
            logger.info("token_move: creature %s not found", creature_id)
            return
        if not creature.is_player:
            logger.info("token_move: creature %s is not a player", creature_id)
            return

        gx_int, gy_int = int(round(gx)), int(round(gy))
        creature.position = (gx_int, gy_int)
        print(f"[PlayerView] token_move: {creature.name} -> ({gx_int}, {gy_int})")

        # Notify the DM viewer
        if self._on_token_moved:
            self._on_token_moved(creature_id, gx_int, gy_int)
        else:
            print("[PlayerView] WARNING: no on_token_moved callback set")

        # Broadcast updated state to all clients
        self.broadcast_state()

    # -- Internal ----------------------------------------------------------

    def _run(self) -> None:
        """Background thread entry point — runs HTTP + WebSocket on the same port."""
        if websockets is not None:
            # Preferred path: use websockets library for both HTTP and WS
            # on the same port via process_request hook
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._ws_main())
            except Exception as e:
                logger.error("Server error: %s", e)
            finally:
                try:
                    self._loop.close()
                except Exception:
                    pass
                self._loop = None
        else:
            # Fallback: HTTP-only mode (no WebSocket support)
            logger.warning(
                "websockets library not installed — running HTTP-only mode"
            )
            handler_cls = partial(_PlayerHTTPHandler, self)
            self._http_server = HTTPServer(("0.0.0.0", self.port), handler_cls)
            logger.info("HTTP-only server listening on 0.0.0.0:%d", self.port)
            while self._running:
                self._http_server.handle_request()

    async def _ws_main(self) -> None:
        """Start a combined WebSocket + HTTP server on self.port."""
        server_self = self  # capture for closures

        async def handler(websocket):
            """Handle a new WebSocket connection."""
            server_self._ws_clients.add(websocket)
            logger.info(
                "Player connected (%s) — %d total",
                websocket.remote_address,
                len(server_self._ws_clients),
            )
            try:
                # Send initial state immediately
                state = server_self.get_player_state()
                state["map_changed"] = True  # force map load on connect
                await websocket.send(json.dumps(state))

                # Listen for player actions (token moves)
                async for message in websocket:
                    try:
                        msg = json.loads(message)
                        print(f"[PlayerView] WS received: {msg.get('type')} from {websocket.remote_address}")
                        if msg.get("type") == "token_move":
                            server_self._handle_player_token_move(msg)
                    except Exception as e:
                        print(f"[PlayerView] Bad client message: {e}")
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception as e:
                logger.debug("WS handler error: %s", e)
            finally:
                server_self._ws_clients.discard(websocket)
                logger.info(
                    "Player disconnected — %d remaining",
                    len(server_self._ws_clients),
                )

        async def process_request(connection, request):
            """
            Intercept HTTP requests before WebSocket upgrade.
            Serve HTML, map images, and token images for non-WS requests.
            """
            path = request.path.split("?")[0]

            # Let WebSocket upgrade requests pass through
            if path == "/ws":
                return None

            if path == "/" or path == "/index.html":
                body = PLAYER_HTML.encode("utf-8")
                return websockets.http11.Response(
                    200,
                    "OK",
                    websockets.datastructures.Headers({
                        "Content-Type": "text/html; charset=utf-8",
                        "Content-Length": str(len(body)),
                        "Cache-Control": "no-cache",
                    }),
                    body,
                )

            if path == "/map":
                map_path = server_self._map_path
                if not map_path or not os.path.isfile(map_path):
                    return websockets.http11.Response(
                        204,
                        "No Content",
                        websockets.datastructures.Headers({}),
                        b"",
                    )
                mime, _ = mimetypes.guess_type(map_path)
                if not mime:
                    mime = "image/jpeg"
                try:
                    with open(map_path, "rb") as f:
                        data = f.read()
                    return websockets.http11.Response(
                        200,
                        "OK",
                        websockets.datastructures.Headers({
                            "Content-Type": mime,
                            "Content-Length": str(len(data)),
                            "Cache-Control": "no-cache",
                        }),
                        data,
                    )
                except Exception:
                    return websockets.http11.Response(
                        500,
                        "Error",
                        websockets.datastructures.Headers({}),
                        b"Map read error",
                    )

            if path.startswith("/token/"):
                creature_id = path.split("/token/", 1)[-1]
                enc = server_self._encounter
                if enc:
                    for c in enc.creatures:
                        if c.id == creature_id and c.token_path and os.path.isfile(c.token_path):
                            mime, _ = mimetypes.guess_type(c.token_path)
                            if not mime:
                                mime = "image/png"
                            try:
                                with open(c.token_path, "rb") as f:
                                    data = f.read()
                                return websockets.http11.Response(
                                    200,
                                    "OK",
                                    websockets.datastructures.Headers({
                                        "Content-Type": mime,
                                        "Content-Length": str(len(data)),
                                        "Cache-Control": "public, max-age=300",
                                    }),
                                    data,
                                )
                            except Exception:
                                pass
                return websockets.http11.Response(
                    404,
                    "Not Found",
                    websockets.datastructures.Headers({}),
                    b"Token not found",
                )

            return websockets.http11.Response(
                404,
                "Not Found",
                websockets.datastructures.Headers({}),
                b"Not found",
            )

        # Try to bind, retrying briefly if port is still in TIME_WAIT
        ws_server = None
        for attempt in range(5):
            try:
                ws_server = await websockets.asyncio.server.serve(
                    handler,
                    "0.0.0.0",
                    self.port,
                    process_request=process_request,
                )
                print(f"[PlayerView] Listening on 0.0.0.0:{self.port} — {self.get_url()}")
                break
            except OSError as e:
                if attempt < 4:
                    print(f"[PlayerView] Port {self.port} busy, retrying ({attempt+1}/5)...")
                    await asyncio.sleep(1)
                else:
                    print(f"[PlayerView] Cannot bind port {self.port}: {e}")
                    return

        # Run until stopped
        while self._running:
            await asyncio.sleep(0.5)

        # Cleanup
        ws_server.close()
        await ws_server.wait_closed()

        # Close all remaining client connections
        if self._ws_clients:
            await asyncio.gather(
                *[
                    ws.close(1001, "Server shutting down")
                    for ws in list(self._ws_clients)
                ],
                return_exceptions=True,
            )
            self._ws_clients.clear()

    async def _async_broadcast(self) -> None:
        """Send player state to all connected WebSocket clients."""
        if not self._ws_clients:
            return

        state = self.get_player_state()
        payload = json.dumps(state)

        dead: list = []
        for ws in list(self._ws_clients):
            try:
                await ws.send(payload)
            except websockets.exceptions.ConnectionClosed:
                dead.append(ws)
            except Exception as e:
                logger.debug("Broadcast send error: %s", e)
                dead.append(ws)

        for ws in dead:
            self._ws_clients.discard(ws)
