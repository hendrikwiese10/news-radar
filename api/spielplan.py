from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone

UA = 'Mozilla/5.0 (compatible; NewsRadarSpielplan/2.0)'

# 1. Bundesliga, 2. Bundesliga, DFB-Pokal - deckt alle Footique-Vereine ab.
LEAGUES = ['bl1', 'bl2', 'dfb']


def current_season():
    now = datetime.now(timezone.utc)
    # Saison "2026" bei openligadb.de läuft von Sommer 2026 bis Sommer 2027.
    return now.year if now.month >= 7 else now.year - 1


def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))


def get_club_matches(club):
    club_l = club.lower()
    season = current_season()
    matches = []

    for league in LEAGUES:
        for s in (season, season + 1):
            url = f'https://api.openligadb.de/getmatchdata/{league}/{s}'
            try:
                data = fetch_json(url)
            except Exception:
                continue
            for m in data:
                t1 = m.get('team1', {}).get('teamName', '')
                t2 = m.get('team2', {}).get('teamName', '')
                if club_l not in t1.lower() and club_l not in t2.lower():
                    continue
                is_home = club_l in t1.lower()
                dt = m.get('matchDateTime') or ''
                date, _, time = dt.partition('T')
                matches.append({
                    'date': date or None,
                    'time': time[:5] if time else None,
                    'competition': m.get('leagueName') or league,
                    'home': t1,
                    'away': t2,
                    'isHome': is_home,
                    'opponent': t2 if is_home else t1,
                    'finished': bool(m.get('matchIsFinished')),
                })

    matches.sort(key=lambda x: (x['date'] or '', x['time'] or ''))
    return matches


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
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

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
