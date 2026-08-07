from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        query = params.get('q', [''])[0]

        if not query:
            self._json(400, {'error': 'Parameter q fehlt'})
            return

        rss_url = (
            f'https://news.google.com/rss/search?q={urllib.parse.quote(query)}'
            f'&hl=de&gl=DE&ceid=DE:de'
        )

        try:
            req = urllib.request.Request(rss_url, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; NewsRadar/1.0)'
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()

            root = ET.fromstring(raw)
            cutoff = datetime.now(timezone.utc) - timedelta(days=3)
            articles = []

            for item in root.iter('item'):
                title = item.findtext('title') or ''
                link = item.findtext('link') or ''
                pub = item.findtext('pubDate') or ''
                src = item.findtext('source') or 'Google News'

                try:
                    dt = parsedate_to_datetime(pub)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    dt = datetime.now(timezone.utc)

                if dt < cutoff:
                    continue

                articles.append({
                    'title': title,
                    'link': link,
                    'pubDate': pub,
                    'source': src,
                    'timestamp': int(dt.timestamp() * 1000),
                })

                if len(articles) >= 15:
                    break

            self._json(200, {'articles': articles})

        except Exception as e:
            self._json(500, {'error': str(e)})

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
