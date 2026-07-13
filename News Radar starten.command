#!/bin/bash
cd "$(dirname "$0")"
# Bereits laufende Instanz beenden
lsof -ti:3456 | xargs kill -9 2>/dev/null
sleep 1
# Server starten
python3 server.py &
sleep 2
# Browser öffnen
open http://localhost:3456
