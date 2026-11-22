# Phase 4 – vorbereitete Choreografien im Browser

## Bedienung

1. Tanztrainer über HTTPS oder auf demselben PC über `http://localhost:8000`
   öffnen. `index.html`, `src/` und **`shared/`** müssen zum selben Stand gehören.
   Direkter HTML-Doppelklick reicht für Worker/Web Crypto nicht aus.
2. Unter **Vorbereitete Choreografie laden** die `.choreo`-Datei aus dem
   Windows-Analyzer auswählen. Video/Punkte bleiben lokal. **Paketimport
   abbrechen** stoppt die Prüfung; die bisherige Referenz bleibt bei Fehler
   oder Abbruch erhalten. Erfolgreiches Ersetzen entfernt alte Aufnahmen und
   Bildpaare, damit diese nicht mit einer anderen Referenz ausgewertet werden.
3. **Qualität und Warnungen des Pakets** lesen. **Referenz abspielen /
   pausieren** benötigt weder Modell noch Kamera. Die Zoom-Checkbox schaltet
   den festen Paketausschnitt aus/ein. „Rechte Bildhälfte“ ist beim Paket
   gesperrt: die Person wurde bereits am PC ausgewählt.
4. Zum Training weiterhin **Erkennung laden**, **Kamera erlauben**, **Training
   starten**. Nur die Modellinstallation lädt wie bisher Dateien von Google/
   jsDelivr. Paketimport und Referenzvorschau erzeugen keine externen Requests.
   Die Erkennung verarbeitet nur die Kamera; auch die Nachanalyse liest
   Referenzposen aus dem Paket. Countdown, Aufnahme, Splitbild, Spiegelung,
   Hintergrundeffekte und Bildpaare bleiben verfügbar.
5. **Referenz schließen** gibt Video und Posepuffer frei. Alternativ eine normale
   Videodatei laden: dann gelten wieder bisherige Referenzinferenz und Autozoom.

Lokal in der Repositorywurzel `.\.venv\Scripts\python -m http.server 8000`
starten. Android benötigt für die Kamera weiterhin HTTPS; HTTP über LAN-IP
reicht nicht. Vercel: Other, Root `.`, kein Build, Output `.`, `shared/` mit
veröffentlichen. GitHub-Pages-Konfiguration unverändert; kein Python-Backend.
Der PR führt selbst weder Merge noch Deployment aus.

## Integrität und Ressourcen

`choreo-worker.js` prüft das unveränderte `showtanz-choreo 1.0.0` mit dem
gemeinsamen Schema und `validation-spec.json`: exakte ZIP-Pfade, lokale/
zentrale Header, Überlappungen/Deskriptoren, reguläre Einträge, STORE/DEFLATE,
CRC, SHA-256, UTF-8/JSON mit Duplicate-Key-/Tiefenprüfung, Manifest, sämtliche
Pose-/Zeitwerte, Binärlängen, Zoom-/Qualitätskonsistenz und Mediensignaturen.
Der Schema-Prüfer unterstützt den im gemeinsamen Draft-2020-12-Schema
verwendeten Teilumfang; unbekannte Schemaregeln werden abgewiesen.

Vor Decoderzugriff folgen begrenzte MP4-Prüfungen: eine AVC-Videospur,
8 Bit/4:2:0-SPS, aufrechte Identitätsmatrix, passende Abmessungen, höchstens
eine AAC-Spur. Ein separater Videodecoder muss erstes Bild, Größe und Dauer
bestätigen. Erst dann wird die bisherige Referenz ersetzt. Keine vollständige
Prüfung sämtlicher komprimierter Medienbits; spätere Decoderfehler werden
gemeldet. Titel/Warnungen werden ausschließlich als Text angezeigt.

| Browserlimit (bewusst strenger als PC-Format) | Wert |
| --- | --- |
| ZIP / einzelner Eintrag | 64 MiB |
| Summe unkomprimierter Inhalte | 96 MiB |
| JSON je Datei / Tiefe | 1 MiB / 64 Ebenen |
| Kompressionsverhältnis | 100:1 |
| ZIP-Verzeichnis / MP4-Metadaten | 64 KiB / 8 MiB |
| Videopixel insgesamt | 4096 × 2160 |
| Probe durch Videodecoder | 15 s |

Das ist **kein RAM-Spitzenlimit**: Hashpuffer, Blobkopien, Worker, Decoder und
Kamera benötigen zusätzlichen Speicher. Große gültige PC-Pakete werden vorab
abgewiesen; ein kleineres Video im Analyzer vorbereiten. Kein Teilimport.
Abbruch beendet den eigenen Worker/Probe-Decoder; Wechsel/Schließen/Pagehide
widerruft URLs und gibt Puffer frei. Stop/Tabwechsel schließt die Kamera.

Aktuelles Chrome/Edge, HTTPS/localhost, Worker und Web Crypto verwenden.
DEFLATE benötigt `DecompressionStream('deflate-raw')`; Analyzer exportiert
STORE. Fehlende Funktionen werden erklärt, Rohvideoimport bleibt verfügbar.
API-Grundlagen: [Compression Standard](https://compression.spec.whatwg.org/),
[Video-Frame-Zeitpunkte](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback).

## Zeit, Geometrie und Bewertung

- DataView liest Little Endian aus übertragenen Binärpuffern, nur 33 Punkte
  pro Abfrage. Keine Objektliste aller Frames. 3D-Schätzwerte bleiben abrufbar;
  Bewertung weiterhin anhand acht 2D-Gliedmaßenrichtungen.
- Binäre Suche nach dem letzten PTS vor/bei dem Bild. Kein Griff in die Zukunft,
  keine Interpolation. Vor dem ersten PTS, außerhalb der Dauer oder bei mehr als
  **0,2 s** alten Daten keine Referenzpose. Stark abgetastete Pakete können
  entsprechend weniger auswertbare Bilder haben.
- Bei verfügbarer Frame-Callback-API `mediaTime`, bei Seeks/fehlender API
  aktuelle Videoposition als Fallback. Keine konstanten FPS vorausgesetzt;
  Kameralatenz bleibt unkalibriert.
- Missing bleibt Missing; Minimum aus Visibility/Presence, bisherige Schwelle
  0,65 und mindestens sechs von acht Richtungen. Fehlende/zu alte Daten sind
  keine Tanzfehler/Nullpunkte, sondern senken die Auswertbarkeit. Die 30-%-
  Zoomregel des Analyzers senkt **nicht** die Bewertungsschwellen.
- Bewertung nutzt volle Originalgeometrie; Paketzoom ist reine Darstellung mit
  Balken, ohne erneute Grenzanalyse. Hauptansicht bevorzugt das Zielformat
  (Darstellung 1:4 bis 4:1, Canvas maximal 1280 je Kante). Kein Abschneiden des
  Crops; Referenz-Bildpaare zeigen die volle Analyseansicht. Kameraspiegelung
  und „gespiegeltes Nachtanzen“ bleiben getrennt.
- Originalton bei Offset 0 auf Videotimeline. Bei Offset separate lokale
  Audiospur mit Zeit `t - offset`; negative Zeiten/nach Tonende sind Stille.
  Pause/Seek/Tempo synchronisieren die Spur. Aufnahme-Mix routet nur die aktive
  Tonquelle; `audio.source=none` bleibt stumm. Keine Beat-/Latenzkalibrierung.

## Tests

`node tests/choreo.test.cjs`, Python-Suiten `test_choreo_browser_contract.py`
und `test_choreo_browser.py` mittels `unittest discover -s tests -p DATEI -v`.
Die 30 Konformitätsfälle verwenden dieselben Mutationen wie der Python-Leser.
Node prüft zusätzliche ZIP-/JSON-/Adaptergrenzen. Playwright nutzt echte Worker/
Decoder mit synthetischer Kamera/Modell, inklusive Aufnahme/Nachanalyse ohne
Referenzinferenz. `tests/requirements.txt`, jsonschema, Chromium und FFmpeg
installieren, ggf. `CHROMIUM_PATH`/`FFMPEG_PATH` setzen. Vollständige CI-Einrichtung:
`.github/workflows/browser.yml`. Android-Hardware und Trainingsqualität sind
dadurch nicht abgenommen; manueller Plan in `ANDROID_TESTPLAN.md`.
