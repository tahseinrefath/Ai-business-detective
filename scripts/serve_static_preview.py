#!/usr/bin/env python3
"""Local development server mimicking Netlify's static hosting & proxy behavior.
Serves frontend/ and proxies /api/* and /avatar/* to your FastAPI backend (port 5000).
Run:
    1. python app.py                          (FastAPI/Uvicorn backend on port 5000)
    2. python scripts/serve_static_preview.py (Netlify simulation on port 8888)
"""
import http.server
import socketserver
import urllib.error
import urllib.request
from pathlib import Path

PORT = 8888
BACKEND = "http://127.0.0.1:5000"
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


class NetlifyDevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/") or self.path.startswith("/avatar/"):
            return self._proxy()
        # Clean URLs: /login -> /login.html, /dashboard -> /dashboard.html
        path_only = self.path.split("?", 1)[0].rstrip("/")
        if path_only:
            candidate = FRONTEND_DIR / (path_only.lstrip("/") + ".html")
            if candidate.exists():
                query = ("?" + self.path.split("?", 1)[1]) if "?" in self.path else ""
                self.path = "/" + candidate.name + query
        return super().do_GET()

    def do_POST(self):
        return self._proxy()

    def do_PUT(self):
        return self._proxy()

    def do_DELETE(self):
        return self._proxy()

    def do_OPTIONS(self):
        return self._proxy()

    def _proxy(self):
        target_url = BACKEND + self.path
        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))

        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")}
        req = urllib.request.Request(target_url, data=body, headers=headers, method=self.command)

        try:
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ("transfer-encoding", "content-length"):
                        self.send_header(k, v)
                data = resp.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as err:
            self.send_response(err.code)
            for k, v in err.headers.items():
                if k.lower() not in ("transfer-encoding", "content-length"):
                    self.send_header(k, v)
            data = err.read()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(502, f"Proxy error reaching backend at {BACKEND}: {e}")


def main():
    print(f"🕵️  Netlify Local Preview running at: http://localhost:{PORT}")
    print(f"👉 Proxying /api/* and /avatar/* to:  {BACKEND}")
    print("Press Ctrl+C to stop.\n")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), NetlifyDevHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
