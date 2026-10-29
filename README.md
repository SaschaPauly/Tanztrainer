# Karnevals-Showtanz – Codex-Übergabe (Version 12)

**Status:** Unveränderte V12-Funktionalität, lediglich in `index.html`, `src/styles.css` und `src/app.js` aufgeteilt. **Keine Android-Korrektur oder neue Funktion wurde bereits implementiert oder auf einem Android-Gerät getestet.**

## Start

- Für die PC-Vorschau: `python -m http.server 8000` und `http://localhost:8000` öffnen.
- Für den Kameratest auf Android: **HTTPS-Deployment** verwenden, z. B. Vercel. `http://192.168.x.x:8000` ist auf Android normalerweise **kein** sicherer Browserkontext für `getUserMedia`.
- `index.html` als statische Seite veröffentlichen; keine Build-Pipeline erforderlich.
- Im Android-Gerät die HTTPS-Seite **direkt in Chrome** öffnen, nicht in WhatsApp-/Messenger-In-App-Browsern. Website-Berechtigung für Kamera und Android-App-Berechtigung für Chrome prüfen.
- Nach `Erkennung laden` ein lokales Referenzvideo über Dateiauswahl importieren. Das erwähnte `Showtanz_WhatsApp.mp4` liegt **nicht** bei und muss vom Nutzer selbst bereitgestellt werden.
- MediaPipe-Modul und Pose-Modell werden aus jsDelivr/Google geladen. Daher ist die Anwendung nicht vollständig offline.

## Projektstruktur

- `index.html`: UI/DOM, unveränderte V12-Markupstruktur.
- `src/styles.css`: bisheriger Inline-CSS-Code.
- `src/app.js`: bisheriger Inline-JavaScript-Code (nicht refaktoriert).
- `original/Tanztrainer V 12.html`: unveränderte Ausgangsdatei zur Regression.
- `AGENTS.md`: verbindlicher Codex-Arbeitsauftrag.
- `docs/IMPLEMENTATION_PLAN.md`: technische Phasen und konkrete Akzeptanzkriterien.
- `docs/ANDROID_TESTPLAN.md`: Diagnose und manuelle Tests.

## Datenschutz

Kamera- und Videobilder werden in der bestehenden Implementierung im Browser verarbeitet; es ist kein eigener Upload-Endpunkt vorhanden. Externe Modell-/Skript-Downloads erzeugen Netzwerkanfragen zu Drittanbietern. Keine Telemetrie oder externen Bild-Uploads ohne ausdrückliche Freigabe hinzufügen. Browser-Aufnahmen nur nach ausdrücklicher Nutzeraktion erzeugen und lokal speichern.

## Technische Grenzen des Ist-Stands

- Rechte Tänzerin wird über **rechte Bildhälfte** zugeschnitten, nicht per zuverlässigem Personen-Tracking.
- MediaPipe `PoseLandmarker` mit `runningMode: IMAGE`, synchronem `detect()`, nur eine Pose.
- Ähnlichkeit vergleicht acht Arm-/Beinsegmentrichtungen; keine verlässliche Beat-/Stilbewertung.
- Zeitversatz ist heuristisch und enthält Kameralatenz.
- Aufnahmen via `canvas.captureStream()` und `MediaRecorder` sind browserabhängig.
- Auf Android wurden Funktion, Berechtigungen, Performance und Audio-Synchronität **nicht verifiziert**.

## Auftrag an Codex

Lies zuerst `AGENTS.md`, danach `docs/IMPLEMENTATION_PLAN.md`. Beginne mit Phase 0/1 (Android-Kamerazugriff), führe nachvollziehbare Tests durch und dokumentiere Browser-/Gerätegrenzen. Keine unbestätigten Erfolgsmeldungen.
