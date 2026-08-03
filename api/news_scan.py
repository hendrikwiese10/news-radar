from http.server import BaseHTTPRequestHandler
import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'


def call_claude(user_content, system_prompt=None, tools=None, max_tokens=2048):
    api_key = os.environ['ANTHROPIC_API_KEY']
    payload = {
        'model': 'claude-opus-5',
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': user_content}],
    }
    if system_prompt:
        payload['system'] = system_prompt
    if tools:
        payload['tools'] = tools

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        try:
            detail = json.loads(detail)['error']['message']
        except Exception:
            pass
        raise RuntimeError(f'Claude API Fehler ({e.code}): {detail}') from e


def extract_text(response):
    return '\n'.join(
        b.get('text', '') for b in response.get('content', []) if b.get('type') == 'text'
    ).strip()


CATEGORIES = ['Transfer', 'Debüt', 'Rekord', 'Auszeichnung', 'Starke Leistung', 'Medienbericht']


def build_prompt(players):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    players_json = json.dumps(players, ensure_ascii=False)

    return f"""Heutiges Datum: {today}.

Du unterstützt einen Scout im Nachwuchsfußball (Future Ballers) dabei, absolut
up to date zu bleiben über die Fußball-Jahrgänge 2010 bis 2012 (Spieler, die
aktuell ca. 14 bis 16 Jahre alt sind) - weltweit, nicht nur in Deutschland.

Gesucht sind aktuelle Ereignisse (idealerweise der letzten 7-14 Tage) aus
folgenden Kategorien: {', '.join(CATEGORIES)}.
- Transfer: Wechsel, Leihe, Vertragsunterschrift
- Debüt: erstes Spiel für eine neue Mannschaft/Auswahl (z.B. Profi-Debüt,
  Nationalmannschafts-Debüt)
- Rekord: z.B. jüngster Torschütze, jüngster Startelf-Spieler etc.
- Auszeichnung: Preise, Nominierungen, auffällige Rankings von Fußball-Medien
- Starke Leistung: Spiele mit vielen Toren/Vorlagen oder auffälligen Statistiken
- Medienbericht: auffällige Berichterstattung, große Portraits, virale Videos

Du hast ZWEI Aufgaben:

1) Gezielte Suche zu den folgenden bereits beim Scout getrackten Spielern
   (Liste als JSON beigefügt): prüfe für jeden Spieler aktiv, ob es in den
   letzten Tagen etwas Neues aus den obigen Kategorien gibt.

Getrackte Spieler:
{players_json}

2) OFFENE Entdeckungssuche (WICHTIGSTER TEIL dieser Aufgabe): suche im Web
   unabhängig von der obigen Liste nach herausragenden, wirklich
   außergewöhnlichen Storys zu Spielern der Jahrgänge 2010-2012 weltweit -
   auch zu Spielern, die der Scout noch gar nicht auf dem Schirm hat. Der
   Anspruch ist NICHT "irgendeine News", sondern etwas, das ein Scout
   unbedingt mitbekommen sollte (z.B. ein 14-Jähriger debütiert in einer
   Profi-Liga, ein Topklub verpflichtet einen 15-Jährigen, ein
   Jahrgang-2011-Spieler stellt einen Rekord auf, große internationale Medien
   berichten über ein Nachwuchstalent).

Antworte AUSSCHLIESSLICH mit einem JSON-Array, kein Fließtext davor oder
danach, kein Markdown-Codeblock. Jedes Element hat exakt diese Form:
{{"category": "Transfer|Debüt|Rekord|Auszeichnung|Starke Leistung|Medienbericht",
"player": "Name des Spielers", "club": "aktueller Verein oder null",
"nation": "Nationalität oder null", "birthYear": Jahrgang als Zahl oder null,
"headline": "1 prägnanter Satz, was passiert ist",
"why": "1 kurzer Satz, warum das bemerkenswert ist",
"tracked": true wenn der Spieler in der obigen Liste steht sonst false,
"sourceTitle": "Titel der Quelle", "sourceUrl": "URL der Quelle"}}

Nur Spieler der Jahrgänge 2010-2012 (bzw. wo der Jahrgang unklar ist, das
Alter aber klar in diesem Bereich liegt). Maximal 20 Einträge, sortiert nach
Relevanz/Außergewöhnlichkeit absteigend. Wenn du zu einem Punkt nichts
Verlässliches findest, lass ihn weg - erfinde nichts. Wenn du gar nichts
Verlässliches findest, gib ein leeres Array [] zurück."""


def get_news_scan(players):
    prompt = build_prompt(players)

    response = call_claude(
        user_content=prompt,
        tools=[{'type': 'web_search_20260209', 'name': 'web_search', 'max_uses': 20}],
        max_tokens=4096,
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

    findings = []
    for item in data:
        if not isinstance(item, dict):
            continue
        category = str(item.get('category', '')).strip()
        player = str(item.get('player', '')).strip()
        headline = str(item.get('headline', '')).strip()
        if not player or not headline:
            continue
        findings.append({
            'category': category if category in CATEGORIES else 'Medienbericht',
            'player': player[:100],
            'club': (str(item.get('club')).strip() if item.get('club') else None),
            'nation': (str(item.get('nation')).strip() if item.get('nation') else None),
            'birthYear': item.get('birthYear') if isinstance(item.get('birthYear'), int) else None,
            'headline': headline[:300],
            'why': str(item.get('why', '')).strip()[:300],
            'tracked': bool(item.get('tracked')),
            'sourceTitle': str(item.get('sourceTitle', '')).strip()[:150] or None,
            'sourceUrl': (str(item.get('sourceUrl')).strip() if item.get('sourceUrl') else None),
        })

    return findings[:20]


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        raw = self.rfile.read(length) if length else b''
        try:
            body = json.loads(raw.decode('utf-8')) if raw else {}
        except json.JSONDecodeError:
            self._json(400, {'error': 'Ungültiges JSON'})
            return

        players = body.get('players') or []
        if not os.environ.get('ANTHROPIC_API_KEY'):
            self._json(500, {'error': 'ANTHROPIC_API_KEY ist nicht konfiguriert'})
            return

        try:
            findings = get_news_scan(players)
            self._json(200, {'findings': findings})
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
