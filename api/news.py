from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Google-News-Ausgabe je Spielernation: (hl = Sprache, gl = Land, ceid = Land:Sprache).
# Damit werden z.B. englische Spieler in der britischen News-Ausgabe gesucht statt
# in der deutschen, wo über sie kaum berichtet wird.
NEWS_LOCALES = {
    'Deutschland': ('de', 'DE', 'DE:de'),
    'Österreich': ('de', 'AT', 'AT:de'),
    'Schweiz': ('de', 'CH', 'CH:de'),
    'England': ('en-GB', 'GB', 'GB:en'),
    'Schottland': ('en-GB', 'GB', 'GB:en'),
    'Wales': ('en-GB', 'GB', 'GB:en'),
    'Irland': ('en-IE', 'IE', 'IE:en'),
    'Frankreich': ('fr', 'FR', 'FR:fr'),
    'Italien': ('it', 'IT', 'IT:it'),
    'Spanien': ('es', 'ES', 'ES:es'),
    'Portugal': ('pt-PT', 'PT', 'PT:pt-150'),
    'Niederlande': ('nl', 'NL', 'NL:nl'),
    'Belgien': ('nl', 'BE', 'BE:nl'),
    'Argentinien': ('es-419', 'AR', 'AR:es-419'),
    'Brasilien': ('pt-BR', 'BR', 'BR:pt-419'),
    'USA': ('en-US', 'US', 'US:en'),
    'Türkei': ('tr', 'TR', 'TR:tr'),
    'Polen': ('pl', 'PL', 'PL:pl'),
    'Kroatien': ('hr', 'HR', 'HR:hr'),
    'Serbien': ('sr', 'RS', 'RS:sr'),
    'Dänemark': ('da', 'DK', 'DK:da'),
    'Schweden': ('sv', 'SE', 'SE:sv'),
    'Norwegen': ('no', 'NO', 'NO:no'),
}
DEFAULT_LOCALE = ('de', 'DE', 'DE:de')


def build_rss_url(query, nation):
    hl, gl, ceid = NEWS_LOCALES.get(nation, DEFAULT_LOCALE)
    return (
        f'https://news.google.com/rss/search?q={urllib.parse.quote(query)}'
        f'&hl={hl}&gl={gl}&ceid={ceid}'
    )


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        query = params.get('q', [''])[0]
        nation = params.get('nation', [''])[0]

        if not query:
            self._json(400, {'error': 'Parameter q fehlt'})
            return

        rss_url = build_rss_url(query, nation)

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
