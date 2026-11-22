# Teststatus

## Phase 3 – native Windows-Oberfläche (2026-11-22)

Umgebung: Windows, Python 3.13, PySide6 6.12.0, vorhandene gepinnte
Analyseabhängigkeiten. Die Windows-CI prüft Python 3.12 und 3.13 einschließlich Qt.

- 116 Python-Fälle: 94 bestehende plus 13 Backend- und neun Qt-Fälle.
  Neue Prüfungen: Abbruch/atomarer Ausgabeschutz, Import ohne Doppelkodierung,
  Aufräumen und FFmpeg-Prozessfreigabe, unveränderte Paketkopie, manuelle
  Personenauswahl/Mehrdeutigkeit/Identität nach langer Lücke, Memory-Mapping,
  tatsächliche Mediengeometrie/Codec-/Dauerprüfung vor der Qt-Vorschau,
  exakte PTS-Auswahl, aufeinanderfolgende Vor-/Rückschritte, Crop-Geometrie,
  Hintergrundarbeit, Schließen während eines Auftrags, Dateisperren und Erhalt
  eines geöffneten Pakets bei Ladefehlern. Ein integrierter Qt-Test durchläuft
  Import → synthetische Analyse → Prüfung → Speichern → SQLite-Ausgabe.
- Acht vorhandene Node-Prüfungen (Vorschau/Zoom), `pip check` und vollständige
  Paketvalidierung erfolgreich. Schema, Fixture und produktive Webdateien
  bleiben unverändert; keine neue Browser-/Android-Funktion behauptet.
- Echter Lite/CPU-Durchlauf über den Desktop-Backendpfad mit lokalem kurzem
  Personenclip: vier Bilder, Qualität `complete`, validiertes Paket gespeichert;
  Fortschrittsstufen Import/Analyse/Export/Öffnen vorhanden. Persönliche
  Video-/Pose-/Modell-/Ergebnisdateien wurden nicht eingecheckt oder hochgeladen.
- Native Windows-Sichtprüfung mit bestehendem 3370-Frame-Lite-Paket:
  Erstbild pausiert, Wiedergabe mit Skelett und festem Zoom, Qualitätswarnungen,
  aufeinanderfolgende Einzelbilder 864/865 bei 28,772/28,805 s geprüft.
  Native Player-Seeks übersprangen anfangs Bilder; separate exakte
  PyAV-Einzelbilddekodierung korrigiert dies. Qt-Komponententests bestätigen
  zusätzlich vollständigen Import-/Exportablauf ohne echte Dateidialogeingabe.

Grenzen: kein eigenständiger EXE-Installer, keine geräteübergreifende
Codec-/Audioabnahme, kein .choreo-Import im Browser und keine Android-Abnahme.
Ein nativer Modell-/Validierungsaufruf ist nicht sofort abbrechbar; Prüfung
zwischen Schritten. Google-Download kann bis zur Netzwerk-Zeitüberschreitung
warten. Qt benötigt zusätzlich Platz für Pakete und lokale Videokopien.
Manuelle Startpersonauswahl und Crop bleiben Heuristiken und müssen visuell
geprüft werden. Doppelklickstarter und Bedienung: `analyzer/README.md`.

## Zoomtoleranz 30 % und getrennte Zeitprüfung (2026-11-22)

- 94 Python-Tests: 82 bisherige plus zwölf Fälle für inklusive 30-%-Grenze und
  Überschreitung, lange Teilverdeckung, drei/vier Rumpfanker, echten Kernverlust,
  Mehrdeutigkeit, getrennte Zeitspannen, 0,5-s-Grenzwert und Paket-Neuberechnung.
- Neuer Paketworkflow erhält Video, Posebytes, Float64-Timestamps, Preview und
  Audiooffset; Quellhash unverändert. Tatsächliche Frameabdeckung gegen den
  Videodecoder geprüft, Sampling und bestehende Ausgaben konservativ behandelt.
- Vorhandenes lokales Lite-Ergebnis ohne neue Inferenz ausgewertet: 23,26 %
  unsichere Bilder, längste Teilunsicherheit 1,867 s, längste Kernlücke 0,200 s.
  Fester Crop x=0,34777, y=0, Breite=0,37302, Höhe=1. Alle 106623 zuverlässig
  gespeicherten Punkte liegen innerhalb. Video-/Pose-/Zeit-/Preview-Hashes
  gegenüber dem ursprünglichen Lite-Paket identisch.
- Neue lokale Vorschau öffnet Lite mit aktivem Zoom. Chrome: korrekte 30-%-
  Anzeige, Großansicht, vier aufeinanderfolgende Schritte, Wiedergabe und
  Zoomumschaltung geprüft; kein JS-Fehler und keine externen Requests. Sichtprüfung.
- Vollständige Sicherheit für verdeckte Bewegungen ist damit nicht belegt;
  Zoom bleibt heuristisch. Trainingsnoten und Konfidenzgrenzen unverändert.

## Skelettvorschau, Einpersonenmodus und Modellvergleich (2026-11-22)

- 82 Python-Tests unter Windows/Python 3.13 erfolgreich: 34 bisherige
  Analyzer-, 30 Format-, fünf Punktexport- und dreizehn neue Vergleichstests.
- Neue Tests: Vordergrundwahl, Wechsel der Kandidatenreihenfolge, mehrdeutige
  Initial-/Zeitzuordnung, abgewiesene Sprünge, dokumentierte Wiederaufnahme,
  konservativer Standardmodus, gültiger Export im expliziten Einpersonenmodus,
  fehlende Modelle, Zeitstempelabgleich, HTML-Script-Escaping, Diagnosewerte,
  kompletter Drei-Modell-Export und Aufräumen bei Fehler im mittleren Modell.
- Lokale Chrome-Prüfung mit synthetischem Fixture: drei Canvas-Skelette,
  Wiedergabezeitpunkt nach Einzelbildschritt 0,25 s, Nummern-/Cropumschaltung,
  kein JavaScript-Fehler und keine HTTP-/HTTPS-Anfragen. Visuell geprüft.
- Zusätzlich echtes lokales Video in Chrome geprüft: vollständige Zeitleiste
  von 112,37 s, vier aufeinanderfolgende Einzelbildschritte bei rationalen PTS,
  Wiedergabe, Großansicht, Nummern und Zoomumschaltung. Kein JavaScript-Fehler
  und keine externen Requests. Vier Node-Regressionstests sichern PTS-Rundung
  bei der Anzeige und frühe/späte Medienmetadaten ab.
- Vollständiger CPU-Vergleich mit je 3370 identischen Zeitpunkten:

  | Modell | Unsichere Bilder | Mindestens 6/8 sichere Arm-/Beinabschnitte | Fehlende Punkte | Gesamtlaufzeit |
  | --- | --- | --- | --- | --- |
  | Lite | 23,26 % | 92,76 % | 594 | 128,76 s |
  | Full | 22,11 % | 92,08 % | 1551 | 161,23 s |
  | Heavy | 51,01 % | 79,64 % | 759 | 287,01 s |

  Werte gelten für dieses lokale Testvideo mit bestätigtem Einpersonenmodus;
  sie sind kein allgemeines Modellranking. Alle drei Paket-Crops bleiben unter
  der geltenden 10-%-Regel beim Ganzbild. Lite ohne Einpersonenmodus hatte im
  früheren Lauf 1089 fehlende Punkte und 23,56 % unsichere Bilder. Modelle und
  persönliche Videos/Posen/Vorschaubilder wurden nicht eingecheckt/hochgeladen.
- Einpersonenverfolgung bleibt heuristisch, zusätzliche Erkennungen sind keine
  Bestätigung realer Nebenpersonen. Modellkonfidenzen sind keine gemessenen
  Fehlerquoten oder Trainingsnoten. Echte Bewegungsgüte braucht Sichtprüfung.
- Vorschau und Diagnose sind unabhängig von der bestehenden Browseranwendung;
  Paketformat, Fixture und produktive Webdateien bleiben unverändert.

## Zoomtoleranz 10 % (2026-11-22)

- 69 Python-Tests unter Windows/Python 3.13 erfolgreich: 34 Analyzer-,
  30 Format- und fünf Punktexporttests.
- Sieben neue Fälle: genau 10 % erlaubt, nächstes unsicheres Bild darüber
  verworfen, strenge 0-%-Option, ungültige Grenzen, langer zusammenhängender
  Ausfall trotz eingehaltenem Prozentbudget, zuverlässige Extrema in partiellen
  Bildern, keine Doppelzählung mehrerer Fehlerarten, Rand-/Zeitlücken-Fallback
  und schemaidentischer Export mit bytegleichen Posewerten (mehrere Aspekte
  in einzelnen Testfällen kombiniert).
- Prozentanteil zählt unsichere Bilder, nicht einzelne Gelenke. Für das
  bisherige lokale Referenzpaket sind 794/3370 = rund 23,6 % unsicher;
  eine 10-%-Grenze hebt dessen Ganzbild-Fallback daher nicht auf.
- Keine Änderung an produktiven Webdateien, Formatvertrag oder Fixture.

## Separate Haltungspunkt-Testausgabe (2026-11-22)

- Fünf neue Windows-/Python-3.13-Tests erfolgreich: CSV/SQLite exakt gegen
  Float32-Punkte und Float64-Zeiten des Fixtures geprüft, fehlende Koordinaten
  als leer/NULL, kein Überschreiben, keine Ausgabe für ungültige Pakete,
  temporäre Daten bei Abbruch aufgeräumt. Originalpaket per Hash unverändert.
- Lokales Referenzpaket separat exportiert: 3370 Zeitpunkte, 111210 Punkte,
  1089 fehlende Punkte in 33 Frames und 761 weitere Frames mit niedriger
  Konfidenz bei vorhandenen Punkten. Damit ist der Ganzbild-Fallback des
  derzeitigen konservativen Zoomalgorithmus erklärbar. Keine Medien oder
  persönlichen Bewegungsdaten eingecheckt/hochgeladen.
- Der Zoom ist Metadatum und verändert das Paketvideo nicht physisch. In
  diesem Schritt weder Crop-Regeln noch Schema oder Browserplayer geändert.
- Windows-CI prüft den neuen Export zusätzlich zu Analyzer und Paketvalidator.

## Analyzer-Importkorrektur (2026-11-22)

Ein reales Referenzvideo enthält für das Pixelseitenverhältnis den Wert `0/1`
(nicht angegeben). Die erste Version wies dies fälschlich als nichtquadratische
Pixel ab. Der Import akzeptiert nun `None`, `0/1` und `1/1` und schreibt
quadratische Pixel explizit in das normalisierte Paketvideo, ohne Bildmaße
zu ändern. Tatsächlich nichtquadratische Pixel werden weiterhin abgewiesen.

- 27 Analyzertests und 30 Formattests unter Windows/Python 3.13 erfolgreich.
- Neuer Regressionstest mit realem FFmpeg/PyAV: synthetische Quelle mit
  `SAR=0/1`, vollständiger CLI-Analysepfad mit synthetischer Engine, gültiger
  Export, SAR danach `1/1`, unveränderte Bildmaße und sämtliche PTS identisch.
- Bestehende VFR-/Audio-/Rotations-/Full-Range-Tests weiterhin erfolgreich.
- Zusätzlicher Präzisionstest für echte Zeitpunkte zwischen nominalen FPS:
  synthetische 30-fps-Quelle mit 5-ms-Versatz ab Frame 4. Mit
  `-enc_time_base:v demux` erhält der Import die Original-PTS anstatt sie
  auf das nominale FPS-Raster zu runden.
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
