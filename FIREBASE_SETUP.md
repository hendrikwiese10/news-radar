# Setup – News Radar (geteilte Live-Datenbank)

News Radar synchronisiert die Spielerliste jetzt live über eine kostenlose
Firebase-Datenbank (Firestore), statt sie nur im Browser zu speichern. Wer
auch immer die Seite öffnet (du oder dein Mitarbeiter) sieht sofort den
aktuellen Stand, und Änderungen erscheinen bei allen live - kein Export/
Import mehr nötig. Es gibt kein sichtbares Login: alle nutzen denselben Link.

## 1. Firebase-Projekt anlegen
1. Gehe zu https://console.firebase.google.com und logge dich mit deinem
   Google-Konto ein.
2. "Projekt hinzufügen" → Name z. B. `news-radar` → Google Analytics kannst
   du deaktivieren → "Projekt erstellen".

## 2. Firestore-Datenbank aktivieren
1. Im Projekt links im Menü: **Build → Firestore Database**.
2. "Datenbank erstellen" → **Produktionsmodus** → Standort z. B. `eur3
   (europe-west)` → "Aktivieren".
3. Tab **Regeln** öffnen, den Inhalt durch den Inhalt der Datei
   [`firestore.rules`](firestore.rules) (aus diesem Ordner) ersetzen →
   "Veröffentlichen".

## 3. Anonyme Anmeldung aktivieren
1. Links im Menü: **Build → Authentication** → "Los geht's".
2. Tab **Sign-in method** → "Anonym" auswählen → aktivieren → Speichern.

(Dadurch gibt es weiterhin **kein sichtbares Login** – die Seite meldet
Besucher automatisch im Hintergrund an, das ist nur nötig, damit die
Datenbank-Regeln greifen.)

## 4. Web-App registrieren & Config kopieren
1. Zahnrad oben links → **Projekteinstellungen**.
2. Ganz unten bei "Meine Apps" → Web-Symbol `</>` klicken.
3. App-Spitzname eingeben (z. B. "News Radar"), **Firebase Hosting NICHT**
   ankreuzen → "App registrieren".
4. Es erscheint ein Code-Block mit `const firebaseConfig = { ... }`. Diese
   Werte kopieren.

## 5. Config in die App eintragen
Öffne [`index.html`](index.html) und suche den Block:

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
Committen & pushen wie gewohnt. Beim ersten Laden der Seite wird die
Datenbank automatisch einmalig mit der aktuellen Spielerliste befüllt.

Diesen Link an dich und deinen Mitarbeiter schicken – fertig, kein Login
nötig, alle sehen und bearbeiten live dieselbe Liste.
