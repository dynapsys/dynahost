import threading
import time
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import List, Optional, Tuple


class VisibleHTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, content: str, server_ip: str, *args, **kwargs):
        self.content = content
        self.server_ip = server_ip
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        client_ip = self.client_address[0]
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.content}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; }}
                .container {{ background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 500px; width: 90%; }}
                h1 {{ color: #333; margin: 0 0 30px 0; font-size: 2.0em; text-align: center; }}
                .info-grid {{ display: grid; gap: 15px; }}
                .info-item {{ background: #f7f9fc; padding: 15px; border-radius: 10px; border-left: 4px solid #667eea; }}
                .label {{ color: #666; font-size: 0.9em; margin-bottom: 5px; }}
                .value {{ color: #333; font-weight: bold; font-size: 1.1em; font-family: 'Courier New', monospace; }}
                .status {{ background: #10b981; color: white; padding: 5px 15px; border-radius: 20px; display: inline-block; margin-top: 20px; }}
                code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌐 {self.content}</h1>
                <div class="info-grid">
                    <div class="info-item"><div class="label">📡 Server IP</div><div class="value">{self.server_ip}</div></div>
                    <div class="info-item"><div class="label">🚪 Port</div><div class="value">{self.server.server_address[1]}</div></div>
                    <div class="info-item"><div class="label">👤 Client IP</div><div class="value">{client_ip}</div></div>
                    <div class="info-item"><div class="label">⏰ Time</div><div class="value">{time.strftime('%H:%M:%S')}</div></div>
                    <div class="info-item"><div class="label">📅 Date</div><div class="value">{time.strftime('%Y-%m-%d')}</div></div>
                </div>
                <center><span class="status">✅ Server running</span></center>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        client_ip = self.client_address[0]
        print(f"   🌐 [{time.strftime('%H:%M:%S')}] Connection from {client_ip} -> {self.server_ip}")


class LANWebServerManager:
    def __init__(self):
        self.servers: List[HTTPServer] = []
        self.threads: List[threading.Thread] = []

    def start_lan_server(self, ip_address: str, port: int, content: str, ssl_context: Optional[ssl.SSLContext] = None) -> Optional[HTTPServer]:
        def handler(*args, **kwargs):
            return VisibleHTTPHandler(content, ip_address, *args, **kwargs)
        try:
            server = HTTPServer((ip_address, port), handler)
            server.timeout = 0.5
            if ssl_context is not None:
                server.socket = ssl_context.wrap_socket(server.socket, server_side=True)

            def serve_forever_with_shutdown():
                while not getattr(server, 'shutdown_requested', False):
                    server.handle_request()

            thread = threading.Thread(target=serve_forever_with_shutdown)
            thread.daemon = True
            thread.start()

            self.servers.append(server)
            self.threads.append(thread)
            scheme = "https" if ssl_context else "http"
            print(f"🌐 {scheme.upper()} server started and visible in LAN:")
            print(f"   📍 Address: {scheme}://{ip_address}:{port}")
            print(f"   📝 Content: {content}")
            return server
        except Exception as e:
            print(f"❌ Failed to start server on {ip_address}:{port}: {e}")
            return None

    def test_connectivity(self, ip_address: str, port: int, scheme: str = "http") -> bool:
        try:
            import urllib.request
            ctx = None
            if scheme == "https":
                import ssl as _ssl
                ctx = _ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _ssl.CERT_NONE
            response = urllib.request.urlopen(f"{scheme}://{ip_address}:{port}", timeout=2, context=ctx)
            if response.status == 200:
                print(f"   ✅ Connectivity test: {ip_address}:{port} responds")
                return True
        except Exception:
            print(f"   ❌ Connectivity test: No response from {ip_address}:{port}")
        return False

    def stop_all(self) -> None:
        for server in self.servers:
            try:
                server.shutdown_requested = True
            except Exception:
                pass
