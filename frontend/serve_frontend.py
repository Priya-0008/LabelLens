import http.server
import socketserver
import os
import sys

PORT = 5188
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS headers for static files
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

if __name__ == "__main__":
    print("=" * 65)
    print(" Legal Metrology Compliance Verification Frontend (SIH26034)")
    print(f" Serving UI on http://localhost:{PORT}")
    print(f" Connecting to Backend on http://localhost:8088")
    print("=" * 65)
    
    # Allow socket address reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down frontend server.")
