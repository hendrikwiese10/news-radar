"""Schlanker Claude-API-Client per urllib (kein pip-Paket nötig, damit die
Vercel-Python-Functions ohne requirements.txt/pip-Build zuverlässig deployen –
genau wie news.py/spielplan.py)."""
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
