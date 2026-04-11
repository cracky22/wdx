import threading
import http.server
import socketserver
import json
from tkinter import messagebox

from constants import PORT
from wdx_logger import get_logger

logger = get_logger(__name__)


class WdxHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, app=None, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if hasattr(self.app, "main_window"):
            self.app.root.after(0, self.app.main_window.set_browser_connected, True)

        if self.path == "/api/add_source":
            content_length = int(self.headers.get("Content-Length", 0))

            if content_length == 0:
                logger.warning("POST /api/add_source ohne Body empfangen")
                self.send_response(400)
                self.end_headers()
                return

            raw = self.rfile.read(content_length)
            try:
                post_data = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                logger.warning("POST-Body konnte nicht dekodiert werden: %s", exc)
                self.send_response(400)
                self.end_headers()
                return

            try:
                data = json.loads(post_data)
                logger.debug("POST /api/add_source — url=%s", data.get("url", "?"))
                self.app.root.after(0, lambda: self.app.handle_communication(data))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')

            except json.JSONDecodeError as exc:
                logger.warning("Ungültiges JSON in POST-Body: %s", exc)
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Invalid JSON"}')
        else:
            logger.debug("POST auf unbekannten Pfad: %s", self.path)
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if hasattr(self.app, "main_window"):
            self.app.root.after(0, self.app.main_window.set_browser_connected, True)

        if self.path == "/api/status":
            current_project = getattr(self.app, "current_project_name", None)
            response = {"connected": True, "current_project": current_project}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            super().do_GET()

    def do_HEAD(self):
        if self.path in ("/api/add_source", "/api/status"):
            self.send_response(200)
            self.end_headers()
        else:
            super().do_HEAD()

    def log_message(self, fmt, *args):
        logger.debug("HTTP %s", fmt % args)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def start_server(app):
    def run_server():
        try:
            handler = lambda *args, **kwargs: WdxHTTPRequestHandler(
                *args, app=app, **kwargs
            )
            httpd = ReusableTCPServer(("", PORT), handler)
            app.httpd = httpd
            logger.info("HTTP-Server gestartet auf Port %d", PORT)
            httpd.serve_forever()
        except OSError as exc:
            logger.critical("Server auf Port %d konnte nicht gestartet werden: %s", PORT, exc)
            app.root.after(
                0,
                lambda: messagebox.showerror(
                    "Server Fehler",
                    f"Konnte Server auf Port {PORT} nicht starten.\n{exc}",
                ),
            )
        except Exception as exc:
            logger.exception("Unerwarteter Server-Fehler: %s", exc)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()