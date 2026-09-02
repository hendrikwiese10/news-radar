from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error
import urllib.parse
import json

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def resolve_google_link(url):
    """Löst einen Google-News-Weiterleitungslink zur echten Ziel-URL des Mediums auf.
    Fällt bei jedem Fehler (Timeout, Bot-Sperre, ...) auf die Original-URL zurück,
    statt einen Fehler zu werfen - dann landet man eben wie bisher über Google."""
    for method in ('HEAD', 'GET'):
        try:
            req = urllib.request.Request(url, headers=HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=8) as r:
                return r.geturl()
        except Exception:
            continue
    return url


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        url = params.get('url', [''])[0]

        # Nur Google-News-Links zulassen, damit dieser Endpunkt nicht als
        # allgemeiner URL-Proxy missbraucht werden kann.
        if not url or not url.startswith('https://news.google.com/'):
            self._json(400, {'error': 'Ungültige oder fehlende URL'})
            return

        self._json(200, {'url': resolve_google_link(url)})

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
