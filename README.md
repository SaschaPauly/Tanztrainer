# Karnevals-Showtanz – Codex-Übergabe (Version 12)

**Status:** Autozoom als Kandidat für v1.1.0 (noch keine Veröffentlichung). V12-Funktionen mit ergänztem unabhängigem Kamera-Schnelltest und lokaler Kameradiagnose. Die vorhandene Pose-Erkennung wird zusätzlich für eine statische Video-Voranalyse verwendet; Haltungsbewertung und Countdown bleiben erhalten. Automatisierte Desktop-Browsertests bestehen; **die Android-Geräteabnahme steht aus** (siehe `docs/TEST_RESULTS.md`).

## Automatischer Videozoom

Standardmäßig aktiv. Nach Videoimport und Laden der Erkennung wird der Bewegungsbereich vor dem Training lokal analysiert. Der Ausschnitt bleibt während des Trainings konstant. Bei unsicherer Erkennung bleibt die bisherige Darstellung erhalten; eine laufende Analyse lässt sich überspringen. Die Einstellung und bis zu 20 Ergebnisse werden nach Möglichkeit lokal gespeichert. Rechte Bildhälfte und ganzes Bild werden getrennt analysiert.

Verfahren, Grenzen, Formeln, Cache, Leistung und Android-Abnahme: [Autozoom-Dokumentation](docs/AUTOMATIC_VIDEO_ZOOM.md). Schnelle Bewegungen zwischen Stichproben können trotz Sicherheitsreserve übersehen werden; bei problematischen Clips Zoom ausschalten.

## Start

- Für die PC-Vorschau: `python -m http.server 8000` und `http://localhost:8000` öffnen.
- Für den Kameratest auf Android: **HTTPS-Deployment** verwenden, z. B. Vercel. `http://192.168.x.x:8000` ist auf Android normalerweise **kein** sicherer Browserkontext für `getUserMedia`.
- `index.html` als statische Seite veröffentlichen; keine Build-Pipeline erforderlich.
- Im Android-Gerät die HTTPS-Seite **direkt in Chrome** öffnen, nicht in WhatsApp-/Messenger-In-App-Browsern. Website-Berechtigung für Kamera und Android-App-Berechtigung für Chrome prüfen.
- Zuerst `Kamera testen (bevorzugt vorne)` ausführen. Rohvorschau und Diagnose funktionieren ohne Modell oder Video. Bei Kamera-/Auflösungsproblemen kann `Ohne Kameravorgabe testen` ausdrücklich gewählt werden; es gibt keine automatischen Berechtigungsversuche. `Test stoppen & Kamera ausschalten` beendet auch ausstehende Startversuche.
- Nach `Erkennung laden` ein lokales Referenzvideo über Dateiauswahl importieren. Das erwähnte `Showtanz_WhatsApp.mp4` liegt **nicht** bei und muss vom Nutzer selbst bereitgestellt werden.
- MediaPipe-Modul und Pose-Modell werden aus jsDelivr/Google geladen. Daher ist die Anwendung nicht vollständig offline.

## Projektstruktur

- `index.html`: V12-Oberfläche mit zusätzlichem Kamera-Test- und Diagnosebereich.
- `src/styles.css`: Gestaltung der V12-Oberfläche und Kameradiagnose.
- `src/app.js`: V12-Anwendungslogik mit Anbindung an die Kamerasteuerung.
- `src/zoom.js`: Voranalyse, konservative Ganzkörperrahmen, Cache und statische Ausschnittgeometrie.
- `src/camera.js`: Kamerastart, Rohvorschau, Fehlerbehandlung und lokale Diagnose.
- `tests/test_camera.py`: automatisierte Chromium-Kamera- und V12-Regressionstests.
- `docs/TEST_RESULTS.md`: Testergebnisse und ausdrücklich offene Geräteprüfungen.
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

## Automatisierte Tests

Die Anwendung selbst benötigt keine Paketinstallation. Für die Browsertests werden Python, Playwright, Chromium und FFmpeg (synthetische Zoom-Testclips) benötigt:

```sh
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python -m unittest discover -s tests -v
node --check src/camera.js
node --check src/app.js
node --check src/zoom.js
node tests/zoom.test.cjs
```

`CHROMIUM_PATH` auf den lokalen Chromium-Pfad setzen. Die Tests starten ihren eigenen lokalen Webserver und verwenden ausschließlich eine simulierte Kamera und synthetische Videos. Externe Downloads sind gesperrt; ein Test ersetzt das Pose-Modell gezielt, um Trainingsstart und Aufnahme zu prüfen. Damit werden keine echte Pose-Erkennung, Android-Hardware oder Audio-Synchronität nachgewiesen.

## Statisches HTTPS-Deployment mit Vercel

Repository in Vercel importieren, Framework-Preset **Other**, Repository-Wurzel als Root Directory, keinen Build-Befehl und `.` als Output Directory wählen. `index.html` und der gesamte Ordner `src/` müssen gemeinsam bereitgestellt werden. Für Tests eines Pull Requests ein Preview-Deployment verwenden; diese Änderung führt selbst kein Deployment oder Merge aus. Die erzeugte HTTPS-Adresse direkt in Chrome auf Android öffnen und `docs/ANDROID_TESTPLAN.md` abarbeiten. Es sind keine Anwendungs-Secrets erforderlich; eine Vercel-Verknüpfung muss über das eigene Konto erfolgen.
