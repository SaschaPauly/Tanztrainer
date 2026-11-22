# Teststatus

## Analyzer-Importkorrektur (2026-11-22)

Ein reales Referenzvideo enthält für das Pixelseitenverhältnis den Wert `0/1`
(nicht angegeben). Die erste Version wies dies fälschlich als nichtquadratische
Pixel ab. Der Import akzeptiert nun `None`, `0/1` und `1/1` und schreibt
quadratische Pixel explizit in das normalisierte Paketvideo, ohne Bildmaße
zu ändern. Tatsächlich nichtquadratische Pixel werden weiterhin abgewiesen.

- 26 Analyzertests und 30 Formattests unter Windows/Python 3.13 erfolgreich.
- Neuer Regressionstest mit realem FFmpeg/PyAV: synthetische Quelle mit
  `SAR=0/1`, vollständiger CLI-Analysepfad mit synthetischer Engine, gültiger
  Export, SAR danach `1/1`, unveränderte Bildmaße und sämtliche PTS identisch.
- Bestehende VFR-/Audio-/Rotations-/Full-Range-Tests weiterhin erfolgreich.
- Webdateien, Formatvertrag und Fixture unverändert; `git diff --check` sauber.

## Showtanztrainer 2.0 – Phase 2 (2026-11-22)

Grundlage: Format-PR #4 ist gemergt (`e3975f5`). Geprüft unter Windows x64,
Python 3.13, PyAV 19.0.2, MediaPipe 1.2.3, imageio-ffmpeg 0.8.1
(FFmpeg 9.0.2). Der Paketvertrag `shared/` und das bestehende Fixture sind
unverändert. Keine Kamera-/Video-/Pose-Uploads.

- 25 neue Analyzertests erfolgreich: echte lokale Decoder/Encoder, VFR-PTS,
  Audioeinsatz mit 200 ms Verzögerung (30 ms AAC-Toleranz), physische Rotation,
  Full-Range-Normalisierung, Unicode-/Leerzeichenpfade, 33×7-Layout,
  Hüftursprung, Presence/Missing-Regeln, Zoom über alle Bewegungsgrenzen,
  konservativer Sampling-Fallback, GPU-Initialisierungs-/Inferenzfallback,
  Fehler/Strg+C, Paketbudget, Ablehnung nichtquadratischer Pixel und atomarer
  Export einschließlich konkurrierender Ausgabedatei.
- 30 vorhandene Formattests erfolgreich. Ein plattformabhängiger Testfall
  schreibt Backslashes jetzt direkt in die ZIP-Bytes: Windows normalisiert
  sonst schon beim Testaufbau den Dateinamen. Die bestehende Ablehnung im
  Validator erhielt eine passende Meldung für Pfadnormalisierung statt NUL.
- Echte MediaPipe-Lite-Modellläufe unter Windows: CPU und `auto` mit
  beobachtetem GPU→CPU-Fallback auf synthetischem Blauvideo (vier Frames,
  132 fehlende Gelenke, gültiges `partial`-Paket). Zusätzlich vier Frames
  eines aus dem offiziellen Personen-Testbild erzeugten Videos: 33 erkannte
  Punkte je Frame, 0 fehlende Gelenke, gültiger `complete`-Export. Das ist
  ein Inferenz-Smoke-Test, keine Tanzqualitäts- oder Bewegungsgüteabnahme.
- Modell explizit von Google geladen:
  `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task`;
  Personenbild: `https://storage.googleapis.com/mediapipe-assets/pose.jpg`.
  Beide nur lokal für Smoke-Tests, nicht eingecheckt. Automatisierte Tests
  brauchen weder diese Downloads noch Netzwerkzugriff.
- Vier bestehende Node-Zoomtests, Syntaxprüfungen aller drei produktiven
  JS-Dateien, Fixture-Validierung, `pip check` und `git diff --check` erfolgreich.
- `git diff main -- index.html src original shared tests/fixtures` ist leer.
  Bestehende Browserregressionen wurden in dieser Phase nicht erneut ausgeführt;
  deren bisheriger Stand steht unten. Keine Pages-/Vercel-Konfigurationsänderung.
- Windows-CI für Python 3.12/3.13 ergänzt; ihr Status ist im separaten PR zu
  prüfen. Sie enthält keine Veröffentlichungs- oder Mergeaktion.

Offen: reales Tanzvideo mit Drehungen/Verdeckungen, lange 4K-Aufnahme,
CPU-Speicher-/Laufzeitprofil, reale GPU-Beschleunigung und Android-Geräteabnahme.
Eine einzelne vorgesehene Person ist Voraussetzung; keine Personenauswahl/
Identitätsverfolgung. GUI folgt in 2.0-Phase 3, Browserimport in Phase 4.
Installation, Aufruf und Grenzen: [Analyzer-Anleitung](../analyzer/README.md).

## Autozoom: Teststatus – 2026-11-02

Kandidat für v1.1.0, keine Veröffentlichung. Vorhandene Kameradiagnose-/Baseline-Änderungen sind enthalten; echte Android-Abnahme bleibt offen. Der aktuelle Entwicklungsauftrag autorisiert dieses isolierte Zoom-Inkrement trotz der noch offenen Geräteabnahme der früheren Roadmap.

## Automatisierte Zoom-Prüfungen

Linux, Chromium über Playwright mit simulierter Kamera; keine externen Modellanfragen in der Testsuite. Synthetische MP4-Clips werden mit FFmpeg erzeugt, MediaPipe wird gezielt durch synthetische Pose-Ergebnisse ersetzt. Kein Android-Gerät, kein echtes Tanzvideo verfügbar.

- **13 bestehende Chromium-Kamera-/V12-Regressionstests bestanden**, einschließlich Import, Effekten, Training, Countdown und beider Aufnahmen.
- **6 neue Chromium-Zoomtests bestanden**: unveränderlicher Rahmen während Wiedergabe und gesperrte Auswahl; Cache bei erneutem Import und Einschalten; gespeicherte Einstellung nach Reload; Hochformat und unvollständige Füße; fehlende Person; Überspringen, Abbruch und Timeout; Inhaltsfingerabdruck bei gleichen Dateinamen und Größen; gesperrtes Schreiben in localStorage; adaptive Zwischenproben über die gesamte Videodauer und gleichzeitig aktive simulierte Kamera.
- **4 Node-Geometrietests bestanden**: fünf Quellauflösungen (einschließlich 4K und Hochformat) × vier Zielformate, vollständiger Einschluss der gepolsterten Bewegungsvereinigung; seitliche/weite Armbewegungen; unterschiedliche Körpergrößen/Kameraabstände; fehlende, niedrige Confidence, NaN, außerhalb liegende und degenerierte Posen; Bildrandreserven und deterministische Berechnung.
- JavaScript-Syntax, Python-Testsyntax und `git diff --check` bestanden.

```sh
python -m unittest discover -s tests -v
node tests/zoom.test.cjs
node --check src/camera.js
node --check src/app.js
node --check src/zoom.js
git diff --check
```

Der lokale HTTP-Testserver und Chromium benötigen in der Ausführungsumgebung Socket-/Browserfreigabe außerhalb der Standardsandbox. Die Suite führt keine Uploads durch. FFmpeg ist ausschließlich Testwerkzeug, keine Browserabhängigkeit.

Die Tests prüfen die Ausschnittgeometrie und Ablaufverdrahtung mit bekannten Posen, **keine garantierte Ganzkörpersichtbarkeit bei echter Pose-Erkennung**. Noch offen: reale Modell-/WASM-Laufzeit, Spitzen-Speicher und Analysezeit auf Galaxy S24+, schnelle Zwischenbewegungen, Drehungen/Kostüme/Verdeckungen, Android-Kamera parallel zur Inferenz, Musik-Synchronität und reale Aufnahmen über GitHub Pages HTTPS. Manuelle Schritte in `docs/ANDROID_TESTPLAN.md`, technische Grenzen in `docs/AUTOMATIC_VIDEO_ZOOM.md`. Der bisherige Testbericht folgt als historische Baseline.

---

# Kameradiagnose: Analyse und Teststatus

Stand: 2026-10-29. Dieses Inkrement betrifft den Kamerazugriff; Phase 1 ist noch nicht vollständig abgenommen.

## Ausgangslage und Änderung

Der V12-Kamerastart prüfte bereits isSecureContext und getUserMedia, zeigte aber nur eine generische Fehlermeldung. Das Livevideo war versteckt; die sichtbare Vorschau hing von canvas.captureStream ab. Es gab keinen expliziten Fallback ohne bevorzugte Kamera, keine Diagnose und keine Entwertung ausstehender Berechtigungsanfragen. Stop während eines offenen Dialogs konnte deshalb von einem verspätet erfolgreichen Start überholt werden.

src/camera.js kapselt nun Anfrage, unbearbeitete Vorschau, Wiedergabe-/Bildbereitschaft (10 Sekunden Timeout nach Freigabe), Fehlerhinweise und Abbruch. Die bisherigen Kamera- und Stop-Schaltflächen sind angebunden. Eine fehlende Permissions-API blockiert den Test nicht. enumerateDevices wird erst nach erfolgreicher Freigabe verwendet; angezeigt wird nur die Anzahl der Kameras. Die Browserkennung und Diagnose verbleiben lokal, ohne Speicherung, Telemetrie oder Upload.

PoseLandmarker, detect, Trainingsstart, Scoring, Timing, Audio und Aufnahmeverfahren wurden nicht verändert. Der zentrale Stop-Pfad gibt zusätzlich die Kamerasteuerung frei. Das Original in original/ blieb unverändert.

Weitere bekannte Grenzen der V12 bleiben bestehen: synchrones IMAGE-Inferencing, browserabhängige MediaRecorder-/captureStream-Unterstützung, Canvas-Vollbildvorschau und Audiofreigabe nach Nutzeraktion. Der unabhängige Kameratest läuft ohne diese optionalen APIs; daraus folgt keine Zusage, dass der bestehende Trainingsablauf ohne sie vollständig funktioniert. Dieses Inkrement verändert diese Trainingslogik ausdrücklich nicht.

## Automatisierte Ausführung

Umgebung: Linux, Python 3.12.14, Playwright 1.62.0, Chromium 154.0.8037.57, Node.js 24.19.0. Kein Android-Gerät verfügbar.

```sh
python3 -m unittest discover -s tests -v
node --check src/camera.js
node --check src/app.js
git diff --check
```

Browserlauf: **13 Tests bestanden**, 0 Fehler, 0 fehlgeschlagen, 0 übersprungen. JavaScript-Syntax und Diff-Whitespace geprüft.

| Test | Nachgewiesenes Verhalten |
| --- | --- |
| independent_camera_and_restart | Test ohne Modell/Video, Bild 640×480, kein Mikrofon, keine externen Requests, Stop und Neustart über bestehende Schaltflächen |
| named_errors_and_explicit_fallback | Acht simulierte Fehlernamen mit passenden Hinweisen; genau ein Anfrageversuch, anschließend ausdrücklich gewählter Fallback mit video:true/audio:false |
| insecure_http_origin | Echter unsicherer HTTP-Testursprung wird vor einer Kameraanfrage mit HTTPS-Hinweis abgewiesen |
| missing_camera_api | Fehlende mediaDevices-API wird erklärt |
| android_browser_hints | Vier simulierte Browserkennungen zeigen Hinweise für WebView, Samsung Internet, Firefox und Edge; kein Kompatibilitätsnachweis |
| no_optional_apis_or_permissions_query | Rohkamera funktioniert ohne Permissions-Abfrage, captureStream, MediaRecorder, AudioContext und Fullscreen |
| no_device_enumeration_before_grant | Keine Geräteabfrage vor erfolgreicher Kamerafreigabe |
| stop_cancels_pending_permission_and_stale_stream | Stop entwertet ausstehende Anfrage; verspäteter alter Stream endet, ein neuer Versuch bleibt unbeeinträchtigt |
| stop_while_video_play_pending | Stop beendet Kamera auch bei nicht abgeschlossener Video-Wiedergabe |
| pagehide_visibility_and_track_ended | Tracks und Videoquellen werden bei Pagehide, verborgenem Dokument und Track-Ende freigegeben |
| video_failure_releases_camera | Wiedergabefehler beendet alle erworbenen Kameratracks |
| video_timeout_releases_camera | Nach 10 Sekunden ohne abspielbares Video endet der Stream; Uhr im Test gezielt vorgespult |
| v12_import_effects_training_recording_smoke | Synthetischer lokaler WebM-Import, Crop-Wechsel, Spiegelungs-/Hintergrund-Steuerelemente, Trainingsstart, beide Aufnahme-Downloads und Wiedergabetempo |

Die Tests verwenden echte Chromium-Medien-APIs mit simulierter Kamera. Berechtigungsfehler, Browserkennungen und fehlende APIs werden injiziert. Der V12-Smoke-Test ersetzt ausschließlich das externe Pose-Modul durch einen Testersatz ohne erkannte Posen; er prüft Ablauf und Aufnahme, keine Erkennungsqualität. Kein externer Modell-Download ist für die Suite erforderlich.

## Noch nicht geprüft

- Echtes Android Chrome über öffentliches HTTPS, reale Berechtigungsdialoge, Front-/Rückkamera und belegte Hardware.
- Samsung Internet, Firefox, Edge und Messenger-Browser auf echten Geräten.
- Reale Modell-/WASM-Inferenz, Pose-/Timingqualität, Audio-Synchronität und Langzeitperformance.
- Vollständige V12-Regression mit echtem Tanzvideo einschließlich Nachanalyse und Bildpaaren sowie Geräte-Fallbacks für optionale Trainings-APIs.

Es wurde kein öffentliches HTTPS-Deployment angelegt. Vercel-Anleitung in README.md, manuelle Schritte in docs/ANDROID_TESTPLAN.md. Geräteabnahme und vollständiger Phase-1-Abschluss dürfen erst nach diesen Tests behauptet werden.

## Showtanztrainer 2.0 – Formatgrundlage, 2026-11-16

Umgebung: Linux, Python 3.12, jsonschema 4.26.0, Desktop-Chromium über
Playwright, FFmpeg/libx264, Node.js. Keine echten Kamera-/Personenaufnahmen.

- 30 neue Pakettests bestanden: gültiges STORE/DEFLATE-Paket, JSON-Schema,
  Gelenkregister, defektes ZIP/CRC, fehlende Dateien, falsche SHA-256,
  unbekannte Version, falsche Gelenkanzahl/Binärlänge, nichtmonotone/negative/
  nichtendliche/zu große Zeitstempel, Zoomgrenzen und Zoom-Datentypen,
  inkonsistente Zoomdatei, Traversal/absolute/Windows-Pfade, doppelte Einträge,
  Symlinks, Verschlüsselungsflag, ZIP64-Version, falscher lokaler Header,
  nicht erlaubte Kompression, Größenlimits vor Dekompression und Kompressionsbombe,
  fehlende/ungültige Posewerte, Qualitätskonsistenz, doppelte JSON-Schlüssel,
  NaN/Float-Überlauf und falsche Mediensignaturen.
- Bestehende 19 Chromium-Regressionsfälle bestanden (Kamera/V12/Autozoom).
- Vier Node-Zoomtests bestanden; Syntaxprüfungen für `src/app.js`,
  `src/camera.js`, `src/zoom.js` bestanden.
- CLI validiert `tests/fixtures/synthetic.choreo` erfolgreich. FFprobe bestätigt
  H.264, yuv420p, 160×120, 1,000 s für das selbst erzeugte Beispielvideo.
- `git diff --exit-code -- index.html src original` bestätigt unveränderte
  produktive Webdateien; `git diff --check` ohne Fehler.

Reproduktion: siehe `analyzer/README.md` und Haupt-README. Der erste Versuch
mit Browserregressionen war durch die Sandbox-Sperre für lokale Sockets
blockiert; erneuter Lauf mit erlaubtem Netzwerkzugriff für den lokalen
Testserver erfolgreich. Fehlertext-Erwartungen wurden während der Entwicklung
korrigiert; die oben angegebenen Ergebnisse beziehen sich auf den fertigen Stand.

Grenzen: keine echte Windows-/Android-Geräteabnahme, keine reale
MediaPipe-Analyse, keine vollständige Codecvalidierung durch den
Paketvalidator, kein Browser-.choreo-Importer. Diese Phase ergänzt den
Dateivertrag und Werkzeuge; sie bestätigt keine neuen Trainingsfähigkeiten.
