from http.server import BaseHTTPRequestHandler
import urllib.parse
import json
import os
import re
from datetime import datetime, timezone

from claude_client import call_claude, extract_text


def get_nation_events(nation, age_group):
    age_label = '' if age_group == 'Profis' else f'{age_group}-'
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    prompt = (
        f'Heutiges Datum: {today}. Suche im Web nach konkreten, bereits bekannten '
        f'kommenden Terminen der {nation} {age_label}Nationalmannschaft '
        f'(z.B. Lehrgänge, Länderspiele, Turniere, Sichtungen) in den nächsten Monaten.\n\n'
        f'Antworte AUSSCHLIESSLICH mit einem JSON-Array, kein Fließtext davor oder danach, '
        f'kein Markdown-Codeblock. Jedes Element hat die Form '
        f'{{"date": "YYYY-MM-DD", "title": "Kurzbeschreibung, z.B. Lehrgang oder Gegner"}}. '
        f'Nur Termine ab dem {today}, maximal 10 Einträge, sortiert nach Datum aufsteigend. '
        f'Wenn du keine verlässlichen, konkreten Termine findest, gib ein leeres Array [] zurück - '
        f'erfinde keine Termine.'
    )

    response = call_claude(
        user_content=prompt,
        tools=[{'type': 'web_search_20260209', 'name': 'web_search', 'max_uses': 5}],
        max_tokens=2048,
    )

    if response.get('stop_reason') == 'refusal':
        return []

    full_text = extract_text(response)

    match = re.search(r'\[.*\]', full_text, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []

    events = []
    for item in data:
        if not isinstance(item, dict):
            continue
        date = str(item.get('date', ''))
        title = str(item.get('title', '')).strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date) and title:
            events.append({'date': date, 'title': title[:200]})

    events.sort(key=lambda e: e['date'])
    return events[:10]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        nation = params.get('nation', [''])[0]
        age_group = params.get('ageGroup', [''])[0]

        if not nation or not age_group:
            self._json(400, {'error': 'Parameter nation und ageGroup fehlen'})
            return

        if not os.environ.get('ANTHROPIC_API_KEY'):
            self._json(500, {'error': 'ANTHROPIC_API_KEY ist nicht konfiguriert'})
            return

        try:
            events = get_nation_events(nation, age_group)
            self._json(200, {'events': events})
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
