from http.server import BaseHTTPRequestHandler
import json
import os

from claude_client import call_claude, extract_text

SYSTEM_PROMPT = """Du bist Analyst für die Social-Media-Performance von Future Ballers
(Instagram & TikTok, Content über Nachwuchsfußballtalente Jahrgänge 2010-2012).

Du bekommst eine Liste von Posts der letzten 7 Tage inkl. Metriken (JSON).

Aufgabe:
1. Identifiziere den Top-Post und den Flop-Post der Woche
   (primär nach Engagement Rate = (likes+comments+shares+saves)/reach,
   sekundär nach Reach)

Antworte auf Deutsch, kurz und klar strukturiert mit den Abschnitten
"Top-Post" und "Flop-Post" (jeweils Titel/Thema, Plattform, Reichweite,
Engagement Rate in %, und eine kurze Begründung in 1-2 Sätzen). Gib nur
diese Analyse aus, keine Einleitung."""


def analyze_week(posts):
    response = call_claude(
        user_content=json.dumps(posts, ensure_ascii=False),
        system_prompt=SYSTEM_PROMPT,
        max_tokens=1024,
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
        if not posts:
            self._json(400, {'error': 'Keine Posts übergeben'})
            return
        if not os.environ.get('ANTHROPIC_API_KEY'):
            self._json(500, {'error': 'ANTHROPIC_API_KEY ist nicht konfiguriert'})
            return

        try:
            analysis = analyze_week(posts)
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
