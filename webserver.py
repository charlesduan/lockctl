#!/usr/bin/env python3

import os
from http.server import HTTPServer, BaseHTTPRequestHandler

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        io = open("/var/log/lockctl.log", "rb")
        try:
            io.seek(-1024, 2)
        except OSError:
            io.seek(0, 0)

        first, sep, keep = io.read(1024).partition(b"\n")
        if len(keep) == 0: keep = first

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()

        self.wfile.write(keep)

httpd = HTTPServer(('', 8000), MyHandler)
httpd.serve_forever()
