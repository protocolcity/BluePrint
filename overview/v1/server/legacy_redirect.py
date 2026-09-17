"""Small redirect listeners for retired UI URLs, owned by the one BP process."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ALIASES = {'/desk':'/work', '/tickets':'/work', '/roster':'/agents', '/workspace-map':'/map', '/overview':'/'}


def target(path):
    parsed=urlsplit(path)
    route=ALIASES.get(parsed.path.rstrip('/'),parsed.path)
    return route + ('?' + parsed.query if parsed.query else '')


_ALLOWED_METHODS = 'GET, HEAD'


def listener(host, port, destination):
    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(307)
            self.send_header('Location', f'http://127.0.0.1:{destination}' + target(self.path))
            self.send_header('Content-Length','0')
            self.end_headers()
        def do_HEAD(self):
            self.do_GET()
        def do_POST(self):
            self.send_response(410)
            self.send_header('Content-Length','0')
            self.end_headers()
        def _refuse_method(self):
            self.send_response(405)
            self.send_header('Allow', _ALLOWED_METHODS)
            self.send_header('Content-Length','0')
            self.end_headers()
        do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _refuse_method
        def log_message(self,*args): pass
    return ThreadingHTTPServer((host,port),Redirect)
