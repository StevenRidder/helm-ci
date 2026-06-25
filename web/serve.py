#!/usr/bin/env python3
"""
Helm — web/serve.py   ·   tiny range-capable static server for the demo
--------------------------------------------------------------------------
`python3 -m http.server` does NOT support HTTP Range requests, which the COG
(cog://) layer needs (geotiff.js streams the .tif). This serves web/ with 206
Partial Content support and the right MIME types for .pmtiles / .tif.

    cd web && python3 serve.py          # -> http://localhost:8080
    cd web && python3 serve.py 9000     # custom port
"""
import http.server, os, re, sys, socketserver

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

MIME = {'.pmtiles': 'application/octet-stream', '.tif': 'image/tiff',
        '.geojson': 'application/geo+json'}

class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME.get(ext) or super().guess_type(path)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_GET(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path.split('?')[0])
        if rng and os.path.isfile(path):
            m = re.match(r'bytes=(\d+)-(\d*)', rng)
            if m:
                size = os.path.getsize(path)
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
                end = min(end, size - 1)
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                self.send_header('Content-Length', str(end - start + 1))
                self.send_header('Content-Type', self.guess_type(path))
                self.end_headers()
                with open(path, 'rb') as f:
                    f.seek(start)
                    self.wfile.write(f.read(end - start + 1))
                return
        super().do_GET()

class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == '__main__':
    print(f'Helm demo → http://localhost:{PORT}   (Ctrl-C to stop)')
    Server(('0.0.0.0', PORT), Handler).serve_forever()
