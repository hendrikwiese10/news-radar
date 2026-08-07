#!/usr/bin/env python3
"""
News Radar – lokaler Server
Startet auf http://localhost:3456
Dient als CORS-Proxy für Google News RSS
"""
import http.server
import urllib.request
import urllib.parse
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api'))
from spielplan import get_club_matches
from analyze_week import analyze_week

PORT = 3456
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Stille Logs

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        # ── Zahlen der Woche: KI-Analyse (Wochen-Zusammenfassung + Post-Insights) ─
        if parsed.path in ('/analyze_week', '/api/analyze_week'):
            length = int(self.headers.get('Content-Length', 0) or 0)
            raw = self.rfile.read(length) if length else b''
            try:
                body = json.loads(raw.decode('utf-8')) if raw else {}
            except json.JSONDecodeError:
                self._json(400, {'error': 'Ungültiges JSON'})
                return

            current_week_posts = body.get('currentWeekPosts')
            historical_stats = body.get('historicalStats')
            target_week = body.get('targetWeek')
            if not current_week_posts:
                self._json(400, {'error': 'Keine Posts für die Fokus-Woche übergeben'})
                return
            if not os.environ.get('ANTHROPIC_API_KEY'):
                self._json(500, {'error': 'ANTHROPIC_API_KEY ist nicht konfiguriert'})
                return

            try:
                result = analyze_week(current_week_posts, historical_stats, target_week)
                if result is None:
                    self._json(200, {'weekSummary': None, 'postInsights': [], 'refused': True})
                    return
                self._json(200, result)
            except Exception as e:
                self._json(500, {'error': str(e)})
            return

        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # ── Spielplan-Proxy (openligadb.de) ──────────────────────────────────
        if parsed.path in ('/spielplan', '/api/spielplan'):
            params = urllib.parse.parse_qs(parsed.query)
            club = params.get('club', [''])[0]

            if not club:
                self._json(400, {'error': 'Parameter club fehlt'})
                return

            try:
                matches = get_club_matches(club)
                self._json(200, {'matches': matches})
            except Exception as e:
                self._json(500, {'error': str(e)})
            return

        # ── CORS-Proxy für Google News RSS ──────────────────────────────────
        if parsed.path in ('/news', '/api/news'):
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
                ns = {'media': 'http://search.yahoo.com/mrss/'}
                cutoff = datetime.now(timezone.utc) - timedelta(days=3)
                articles = []

                for item in root.iter('item'):
                    title = item.findtext('title') or ''
                    link  = item.findtext('link') or ''
                    pub   = item.findtext('pubDate') or ''
                    src   = item.findtext('source') or 'Google News'

                    # Datum parsen
                    try:
                        # RFC 2822
                        from email.utils import parsedate_to_datetime
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
            return

        # ── Statische Dateien ────────────────────────────────────────────────
        path = parsed.path.lstrip('/')
        if path == '':
            path = 'index.html'

        file_path = os.path.join(BASE_DIR, path)
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, 'index.html')
        if not os.path.isfile(file_path):
            self.send_response(404)
            self.end_headers()
            return

        ext = os.path.splitext(file_path)[1]
        mime = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css'}.get(ext, 'text/plain')

        with open(file_path, 'rb') as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', len(data))
        self.send_cors()
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(data))
        self.send_cors()
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    os.chdir(BASE_DIR)
    server = http.server.HTTPServer(('localhost', PORT), Handler)
    print(f'✅  News Radar läuft auf  http://localhost:{PORT}')
    print('   Zum Beenden: Ctrl+C')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer gestoppt.')
