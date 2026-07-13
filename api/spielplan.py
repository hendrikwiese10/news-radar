from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

UA = 'Mozilla/5.0 (compatible; NewsRadarSpielplan/1.0)'


class FixtureRowParser(HTMLParser):
    """Parses a fussball.de Staffelspielplan page into (home, away, matchLink) rows.

    Datum/Ergebnis sind auf dieser Seite bewusst über einen Obfuskations-Font
    verschlüsselt (Anti-Scraping-Schutz von fussball.de) - wir lesen sie hier
    nicht aus, sondern holen das Datum pro Spiel separat aus dem <title> der
    Spiel-Detailseite, wo es fussball.de selbst als Klartext veröffentlicht.
    """

    def __init__(self):
        super().__init__()
        self.rows = []
        self._in_tr = False
        self._in_club_name = False
        self._cur_row = None
        self._text_buf = ''

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == 'tr':
            self._in_tr = True
            self._cur_row = {'clubs': [], 'link': None}
        if tag == 'div' and self._in_tr and attrs_d.get('class') == 'club-name':
            self._in_club_name = True
            self._text_buf = ''
        if tag == 'a' and self._in_tr and '/spiel/' in attrs_d.get('href', ''):
            if self._cur_row is not None and self._cur_row['link'] is None:
                self._cur_row['link'] = attrs_d['href']

    def handle_endtag(self, tag):
        if tag == 'div' and self._in_club_name:
            self._in_club_name = False
            if self._cur_row is not None:
                self._cur_row['clubs'].append(self._text_buf.strip())
        if tag == 'tr' and self._in_tr:
            self._in_tr = False
            if self._cur_row and len(self._cur_row['clubs']) == 2 and self._cur_row['link']:
                self.rows.append(self._cur_row)
            self._cur_row = None

    def handle_data(self, data):
        if self._in_club_name:
            self._text_buf += data


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'ignore')


def get_match_date(match_url):
    html = fetch(match_url)
    m = re.search(r'<title>([^<]+)</title>', html)
    if not m:
        return None
    dm = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', m.group(1))
    if not dm:
        return None
    d, mo, y = dm.groups()
    return f'{y}-{mo}-{d}'


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        staffel_url = params.get('staffel', [''])[0]
        club = params.get('club', [''])[0]

        if not staffel_url or not club:
            self._json(400, {'error': 'Parameter staffel und club sind Pflicht'})
            return

        if not staffel_url.startswith('https://www.fussball.de/'):
            self._json(400, {'error': 'Ungültige staffel-URL'})
            return

        try:
            html = fetch(staffel_url)
            parser = FixtureRowParser()
            parser.feed(html)

            club_l = club.lower()
            candidates = [
                row for row in parser.rows
                if club_l in row['clubs'][0].lower() or club_l in row['clubs'][1].lower()
            ]

            matches = []
            for row in candidates[:12]:
                home, away = row['clubs']
                link = row['link']
                if link and link.startswith('/'):
                    link = 'https://www.fussball.de' + link
                date = get_match_date(link) if link else None
                matches.append({
                    'date': date,
                    'home': home,
                    'away': away,
                    'isHome': club_l in home.lower(),
                    'opponent': away if club_l in home.lower() else home,
                    'link': link,
                })

            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            matches = [m for m in matches if m['date'] and m['date'] >= today]
            matches.sort(key=lambda m: m['date'])

            self._json(200, {'matches': matches})

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
