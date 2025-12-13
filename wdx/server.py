import threading
import http.server
import socketserver
import json
from constants import PORT

class WdxHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, app=None, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)

    def do_POST(self):
        if self.path == "/api/add_source":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(post_data)
                self.app.handle_communication(data)
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

def start_server(app):
    handler = lambda *args, **kwargs: WdxHTTPRequestHandler(*args, app=app, **kwargs)
    httpd = socketserver.TCPServer(("", PORT), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    app.httpd = httpd