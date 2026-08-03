from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

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
        with urllib.request.urlopen(req, timeout=60) as r:
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
(Instagram & TikTok, Content über Nachwuchsfußballtalente Jahrgänge 2010-2012).

Du bekommst eine Liste ALLER bisher getrackten Posts (JSON), jeweils mit
Woche (weekId = Montag-Datum der jeweiligen Woche), Plattform, Format,
Metriken und bereits berechneter Engagement Rate
(= (likes+comments+shares+saves)/reach, in %). Die Liste kann mehrere
Wochen umfassen - je mehr Wochen vorliegen, desto besser lassen sich
Trends und Vergleiche ziehen. Eine Fokus-Woche wird dir separat genannt.

Aufgabe:
1. Analysiere die Fokus-Woche im Detail - nicht nur "bester/schlechtester
   Post", sondern WARUM ein Post gut oder schlecht performt hat. Zieh dafür
   alle verfügbaren Metriken heran (Reichweite, Ø Wiedergabedauer im
   Vergleich zur tatsächlichen Videolänge, Likes/Kommentare/Shares/Saves,
   neue Follower, Traffic-Quelle).
2. Vergleiche die Fokus-Woche mit den historischen Daten (falls vorhanden):
   Liegt z.B. die Ø Wiedergabedauer eines Formats unter dem historischen
   Durchschnitt dieses Formats? Ist die Reichweite im Vergleich zu
   vorherigen Wochen gestiegen oder gefallen? Gibt es Auffälligkeiten bei
   bestimmten Formaten, Plattformen oder Traffic-Quellen?
3. Stelle begründete Hypothesen auf, WARUM eine Abweichung vorliegen könnte
   (z.B. schwacher Hook in den ersten Sekunden, ungünstige Posting-Zeit,
   das Format ermüdet die Zielgruppe, Traffic kam kaum über Explore/For You
   statt über den Feed bestehender Follower, etc.) - kennzeichne das klar
   als Vermutung, nicht als Fakt.
4. Gib 2-3 konkrete, umsetzbare Empfehlungen für die kommende Woche, die
   sich direkt aus den Zahlen ableiten.

Falls nur eine einzige Woche an Daten vorliegt, weise kurz darauf hin, dass
belastbare Trendvergleiche erst mit mehr Wochen möglich sind, und
analysiere trotzdem die vorhandene Woche so gut wie möglich.

Antworte auf Deutsch, klar strukturiert (kurze Absätze/Stichpunkte), aber
inhaltlich tiefgehend statt oberflächlich. Keine Einleitung, direkt mit
der Analyse beginnen."""


def analyze_week(posts, target_week=None):
    user_content = json.dumps({'targetWeek': target_week, 'posts': posts}, ensure_ascii=False)
    response = call_claude(
        user_content=user_content,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=2048,
    )
    if response.get('stop_reason') == 'refusal':
        return None
    return extract_text(response)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        raw = self.rfile.read(length) if length else b''
        try:
            body = json.loads(raw.decode('utf-8')) if raw else {}
        except json.JSONDecodeError:
            self._json(400, {'error': 'Ungültiges JSON'})
            return

        posts = body.get('posts')
        target_week = body.get('targetWeek')
        if not posts:
            self._json(400, {'error': 'Keine Posts übergeben'})
            return
        if not os.environ.get('ANTHROPIC_API_KEY'):
            self._json(500, {'error': 'ANTHROPIC_API_KEY ist nicht konfiguriert'})
            return

        try:
            analysis = analyze_week(posts, target_week)
            if analysis is None:
                self._json(200, {'analysis': None, 'refused': True})
                return
            self._json(200, {'analysis': analysis})
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
