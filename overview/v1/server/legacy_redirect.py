"""Small redirect listeners for retired UI URLs, owned by the one BP process."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ALIASES = {'/desk':'/work', '/tickets':'/work', '/roster':'/agents', '/workspace-map':'/map', '/overview':'/'}


def target(path):
    parsed=urlsplit(path)
    route=ALIASES.get(parsed.path.rstrip('/'),parsed.path)
    return route + ('?' + parsed.query if parsed.query else '')


def listener(host, port, destination):
    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(307)
            self.send_header('Location', f'http://127.0.0.1:{destination}' + target(self.path))
            self.send_header('Content-Length','0')
            self.end_headers()
        def do_POST(self):
            self.send_response(410)
            self.send_header('Content-Length','0')
            self.end_headers()
        def log_message(self,*args): pass
    return ThreadingHTTPServer((host,port),Redirect)
