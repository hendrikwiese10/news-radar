# Setup – FutureBallers Wochenplan

Die Seite synchronisiert sich live über eine kostenlose Firebase-Datenbank
(Firestore). Damit es funktioniert, brauchst du einmalig ein eigenes
Firebase-Projekt (5 Minuten, kostenlos, kein Kreditkarte nötig).

## 1. Firebase-Projekt anlegen
1. Gehe zu https://console.firebase.google.com und logge dich mit deinem
   Google-Konto ein.
2. "Projekt hinzufügen" → Name z. B. `futureballers-wochenplan` → Google
   Analytics kannst du deaktivieren → "Projekt erstellen".

## 2. Firestore-Datenbank aktivieren
1. Im Projekt links im Menü: **Build → Firestore Database**.
2. "Datenbank erstellen" → **Produktionsmodus** → Standort z. B. `eur3
   (europe-west)` → "Aktivieren".
3. Tab **Regeln** öffnen, den Inhalt durch den Inhalt der Datei
   `wochenplan/firestore.rules` (aus diesem Ordner) ersetzen → "Veröffentlichen".

## 3. Anonyme Anmeldung aktivieren
1. Links im Menü: **Build → Authentication** → "Los geht's".
2. Tab **Sign-in method** → "Anonym" auswählen → aktivieren → Speichern.

(Dadurch gibt es weiterhin **kein sichtbares Login** für euch – die Seite
meldet Besucher automatisch im Hintergrund an, das ist nur nötig, damit die
Datenbank-Regeln greifen.)

## 4. Web-App registrieren & Config kopieren
1. Zahnrad oben links → **Projekteinstellungen**.
2. Ganz unten bei "Meine Apps" → Web-Symbol `</>` klicken.
3. App-Spitzname eingeben (z. B. "Wochenplan"), **Firebase Hosting NICHT**
   ankreuzen → "App registrieren".
4. Es erscheint ein Code-Block mit `const firebaseConfig = { ... }`.
   Diese Werte kopieren.

## 5. Config in die App eintragen
Öffne [`wochenplan/index.html`](index.html) und suche den Block:

```js
const firebaseConfig = {
  apiKey: "DEIN_API_KEY",
  authDomain: "DEIN_PROJECT.firebaseapp.com",
  projectId: "DEIN_PROJECT",
  storageBucket: "DEIN_PROJECT.appspot.com",
  messagingSenderId: "DEINE_SENDER_ID",
  appId: "DEINE_APP_ID"
};
```

Ersetze ihn durch die kopierten Werte aus Schritt 4. Speichern.

## 6. Deployen
Committen & pushen wie gewohnt – da dieses Repo bereits mit Vercel verbunden
ist, wird die Seite automatisch mitgebaut. Danach ist sie erreichbar unter:

```
https://<eure-vercel-domain>/wochenplan/
```

Diesen Link an dich und deinen Mitarbeiter schicken – fertig, kein Login
nötig, Änderungen synchronisieren sich sofort bei beiden.

## Lokal testen
```
python3 server.py
```
und dann http://localhost:3456/wochenplan/ öffnen (Live-Sync braucht die
oben eingetragene Firebase-Config, sonst zeigt die Seite nur einen
Hinweis-Banner).
