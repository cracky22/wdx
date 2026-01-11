import threading
import http.server
import socketserver
import json
from tkinter import messagebox
from constants import PORT

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
                self.send_response(400)
                self.end_headers()
                return
            
            post_data = self.rfile.read(content_length).decode("utf-8")
            
            try:
                data = json.loads(post_data)
                self.app.root.after(0, lambda: self.app.handle_communication(data))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
                
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Invalid JSON"}')
                
        else:
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

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_server(app):
    def run_server():
        try:
            handler = lambda *args, **kwargs: WdxHTTPRequestHandler(*args, app=app, **kwargs)
            httpd = ReusableTCPServer(("", PORT), handler)
            app.httpd = httpd
            httpd.serve_forever()
        except OSError as e:
            app.root.after(0, lambda: messagebox.showerror("Server Fehler", f"Konnte Server auf Port {PORT} nicht starten.\n{e}"))
        except Exception as e:
            print(f"Server error: {e}")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()