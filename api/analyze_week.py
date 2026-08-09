from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'


def call_claude(user_content, system_prompt=None, tools=None, max_tokens=2048, output_format=None, effort=None):
    api_key = os.environ['ANTHROPIC_API_KEY']
    payload = {
        'model': 'claude-opus-5',
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': user_content}],
    }
    if system_prompt:
        # cache_control: der System-Prompt ist bei jedem Aufruf identisch,
        # dadurch wird er ab dem zweiten Aufruf innerhalb kurzer Zeit stark
        # günstiger verarbeitet statt komplett neu abgerechnet zu werden.
        payload['system'] = [
            {'type': 'text', 'text': system_prompt, 'cache_control': {'type': 'ephemeral'}}
        ]
    if tools:
        payload['tools'] = tools
    output_config = {}
    if output_format:
        output_config['format'] = output_format
    if effort:
        output_config['effort'] = effort
    if output_config:
        payload['output_config'] = output_config

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


SYSTEM_PROMPT = """Du bist Analyst für die Social-Media-Performance von Future Ballers
(Content über Nachwuchsfußballtalente Jahrgänge 2010-2012).

WICHTIG: Bewertet werden ausschließlich Instagram-Posts. TikTok- und
X-Posts sind bereits herausgefiltert und tauchen weder in den Daten
der Fokus-Woche noch in den historischen Vergleichswerten auf.
Beziehe dich in Analyse und Empfehlungen also rein auf Instagram und
stelle keine Plattform-Vergleiche zu TikTok oder X an.

Du bekommst zwei Dinge als JSON:
1. currentWeekPosts: alle Posts der Fokus-Woche (targetWeek), jeweils mit
   eindeutiger id, Plattform, Format, Metriken und bereits berechneter
   Engagement Rate (= (likes+comments+shares+saves)/reach, in %).
2. historicalStats: eine bereits vorverdichtete Zusammenfassung ALLER
   vorherigen Wochen (nicht die Rohdaten einzelner Posts), gruppiert nach
   Format: Anzahl Posts, Ø Reichweite, Ø Engagement Rate und Ø Verhältnis
   Wiedergabedauer/Videolänge in %. Dazu die Gesamtzahl bisher getrackter
   Wochen und Posts. Nutze diese Werte als Vergleichsbasis - je mehr
   historische Wochen vorliegen, desto belastbarer sind Vergleiche.

Aufgabe 1 - weekSummary (Gesamtbild der Fokus-Woche):
- Vergleiche die Fokus-Woche mit historicalStats (falls totalHistoricalWeeks
  > 0): Liegt z.B. die Ø Wiedergabedauer eines Formats unter dem
  historischen Durchschnitt dieses Formats? Ist die Reichweite im
  Vergleich zum historischen Schnitt gestiegen oder gefallen?
  Auffälligkeiten bei bestimmten Formaten oder Traffic-Quellen?
- Gib 2-3 konkrete, umsetzbare Empfehlungen für die kommende Woche.
- Falls totalHistoricalWeeks 0 ist, weise kurz darauf hin, dass belastbare
  Trendvergleiche erst mit mehr Wochen möglich sind, und analysiere
  trotzdem so gut wie möglich anhand der Fokus-Woche allein.
- Klar strukturiert (kurze Absätze/Stichpunkte), inhaltlich tiefgehend
  statt oberflächlich, keine Einleitung, direkt mit der Analyse beginnen.

Aufgabe 2 - postInsights (ein Eintrag pro Post aus currentWeekPosts): Für
jeden Post der Fokus-Woche eine kurze, konkrete Einschätzung anhand seiner
Zahlen (Reichweite, Wiedergabedauer vs. Videolänge, Interaktionen,
Traffic-Quelle, im Vergleich zu den anderen Posts der Woche und - falls
vorhanden - zum historischen Durchschnitt desselben Formats aus
historicalStats):
- wasGut: Was lief bei diesem Post gut? Leerstring falls nichts auffällt.
- merken: Was merken wir uns davon für künftigen Content? Leerstring
  falls nichts.
- wasNicht: Was lief nicht gut? Leerstring falls nichts Negatives auffällt.
- achten: Worauf sollte man bei ähnlichem Content künftig achten?
  Leerstring falls nichts.
- ursache: Vermutete Ursache für eine Auffälligkeit (z.B. schwacher Hook
  in den ersten Sekunden, ungünstige Posting-Zeit, Traffic kam kaum über
  Explore/For You statt über den Feed bestehender Follower, etc.) -
  klar als Vermutung kennzeichnen, nicht als Fakt. Leerstring falls
  unklar oder nicht relevant.
Jedes Feld maximal 1-2 kurze Sätze - keine Romane, das sind Stichpunkt-
artige Kurzeinschätzungen pro Post.

WICHTIG: postInsights MUSS genau einen Eintrag pro Post aus
currentWeekPosts enthalten (Anzahl Einträge = Anzahl Posts in
currentWeekPosts, per postId zuordenbar). Ein leeres postInsights-Array
ist nur zulässig, wenn currentWeekPosts selbst leer ist. Auch wenn zu
einem Post wenig auffällt, trag ihn trotzdem mit möglichst vielen leeren
Feldern ein - nie komplett weglassen."""

POST_INSIGHT_SCHEMA = {
    'type': 'object',
    'properties': {
        'weekSummary': {
            'type': 'string',
            'description': 'Ausführliche Wochenanalyse als Markdown (siehe Aufgabe 1).',
        },
        'postInsights': {
            'type': 'array',
            'description': 'Ein Eintrag pro Post der Fokus-Woche (siehe Aufgabe 2).',
            'items': {
                'type': 'object',
                'properties': {
                    'postId': {'type': 'string'},
                    'wasGut': {'type': 'string'},
                    'merken': {'type': 'string'},
                    'wasNicht': {'type': 'string'},
                    'achten': {'type': 'string'},
                    'ursache': {'type': 'string'},
                },
                'required': ['postId', 'wasGut', 'merken', 'wasNicht', 'achten', 'ursache'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['weekSummary', 'postInsights'],
    'additionalProperties': False,
}


def analyze_week(current_week_posts, historical_stats=None, target_week=None):
    user_content = json.dumps({
        'targetWeek': target_week,
        'currentWeekPosts': current_week_posts,
        'historicalStats': historical_stats or {'totalHistoricalWeeks': 0, 'totalHistoricalPosts': 0, 'byFormat': {}},
    }, ensure_ascii=False)
    response = call_claude(
        user_content=user_content,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=12000,
        output_format={'type': 'json_schema', 'schema': POST_INSIGHT_SCHEMA},
        effort='medium',
    )
    if response.get('stop_reason') == 'refusal':
        return None
    return json.loads(extract_text(response))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
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

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
