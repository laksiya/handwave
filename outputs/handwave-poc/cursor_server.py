"""Loopback-only Windows cursor bridge for the Handwave prototype."""

import ctypes
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765
ALLOWED_ORIGINS = ("http://127.0.0.1:", "http://localhost:")
user32 = ctypes.windll.user32
LEFT_DOWN = 0x0002
LEFT_UP = 0x0004
last_activity = time.monotonic()
mouse_is_down = False
state_lock = threading.Lock()


def release_if_stale():
    global mouse_is_down
    while True:
        time.sleep(0.25)
        with state_lock:
            if mouse_is_down and time.monotonic() - last_activity > 1.5:
                user32.mouse_event(LEFT_UP, 0, 0, 0, 0)
                mouse_is_down = False


class CursorHandler(BaseHTTPRequestHandler):
    def _allowed(self):
        origin = self.headers.get("Origin", "")
        return not origin or origin.startswith(ALLOWED_ORIGINS)

    def _headers(self, status=200):
        self.send_response(status)
        origin = self.headers.get("Origin", "")
        if origin.startswith(ALLOWED_ORIGINS):
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_OPTIONS(self):
        self._headers(204 if self._allowed() else 403)

    def do_GET(self):
        if self.path != "/health" or not self._allowed():
            self._headers(404)
            return
        self._headers()
        self.wfile.write(b'{"ok":true}')

    def do_POST(self):
        global last_activity, mouse_is_down
        if not self._allowed():
            self._headers(403)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 1024)
            data = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/move":
                x = max(0.0, min(1.0, float(data["x"])))
                y = max(0.0, min(1.0, float(data["y"])))
                user32.SetCursorPos(round(x * (user32.GetSystemMetrics(0) - 1)), round(y * (user32.GetSystemMetrics(1) - 1)))
                with state_lock:
                    last_activity = time.monotonic()
            elif self.path == "/mouse":
                action = data.get("action")
                if action not in ("down", "up"):
                    raise ValueError("Invalid mouse action")
                user32.mouse_event(LEFT_DOWN if action == "down" else LEFT_UP, 0, 0, 0, 0)
                with state_lock:
                    last_activity = time.monotonic()
                    mouse_is_down = action == "down"
            else:
                self._headers(404)
                return
            self._headers()
            self.wfile.write(b'{"ok":true}')
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            self._headers(400)
            self.wfile.write(b'{"ok":false}')

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    print(f"Handwave cursor helper running at http://{HOST}:{PORT}")
    print("Keep this window open while using desktop control. Ctrl+C stops it.")
    threading.Thread(target=release_if_stale, daemon=True).start()
    try:
        ThreadingHTTPServer((HOST, PORT), CursorHandler).serve_forever()
    finally:
        user32.mouse_event(LEFT_UP, 0, 0, 0, 0)
