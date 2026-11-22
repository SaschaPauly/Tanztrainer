# Showtanz-Analyzer – Phase 2

Eigenständige lokale Windows-Python-CLI: Video importieren, MediaPipe Pose
Landmarker mit 33 Punkten ausführen und ein validiertes `showtanz-choreo 1.0.0`
schreiben. Keine GUI; Browserimport folgt in Phase 4. Die Webanwendung bleibt
unverändert.

## Windows-Installation

Python **3.12 oder 3.13, 64 Bit**, installieren (getestet: Windows, Python 3.13).
PowerShell in der Repositorywurzel:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r analyzer/requirements-analysis.txt
New-Item -ItemType Directory -Force models | Out-Null
Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task' -OutFile models/pose_landmarker_lite.task
```

Diese Installationsschritte laden Pakete vom konfigurierten Paketindex und das
Modell von Google. `imageio-ffmpeg` enthält FFmpeg für Windows; OpenCV wird von
MediaPipe mitinstalliert. PyAV liefert Decoder/PTS, Pillow Vorschau und
Inferenzverkleinerung. Keine zusätzliche FFprobe-Installation erforderlich.
Die Analyse selbst führt keine Downloads oder Video-/Bild-/Pose-Uploads aus.
Eine vorhandene passende `.task`-Datei ist ebenfalls nutzbar. Eigene Videos,
Modelle und Pakete nicht ins öffentliche Repository einchecken.

Linux: gleiche Modulbefehle mit `.venv/bin/python`. Nur der bestehende
Paketvalidator braucht weiterhin bloß Python 3.11+ und
`analyzer/requirements.txt`; Analyseabhängigkeiten sind separat.

## Aufruf

```powershell
.\.venv\Scripts\python -m analyzer.cli 'C:\Tanzvideos\Training.mp4' 'C:\Tanzvideos\Training.choreo' --model models/pose_landmarker_lite.task --backend auto --title 'Training November'
.\.venv\Scripts\python -m analyzer.validate 'C:\Tanzvideos\Training.choreo'
```

Der Ausgabeordner muss existieren. Leerzeichen in Pfaden sind erlaubt.
Bestehende Dateien werden nur mit `--overwrite` ersetzt, erst nach vollständiger
Validierung. Strg+C entfernt temporäre Dateien und erhält vorhandene Ausgaben.

| Option | Wirkung |
| --- | --- |
| `--backend auto` | Standard: GPU-Erstellung versuchen, bei Initialisierungs-/Inferenzfehler einmal auf CPU wechseln |
| `--backend cpu` | CPU unmittelbar verwenden; CPU-Modellfehler brechen ab |
| `--backend gpu` | GPU bevorzugen, ebenfalls mit CPU-Fallback; keine Zusage von Windows-GPU-Unterstützung |
| `--max-fps 0` | Jeden dekodierten Videoframe analysieren; Standard |
| `--max-fps 15` | Weniger Inferenzarbeit durch zeitliche Abtastung; Zoom verwendet wegen möglicher verpasster Extrema Ganzbild |
| `--max-side 1280` | Größte Bildkante nur für Inferenz verkleinern; Originalvideo und Koordinatensystem erhalten |
| `--aspect 0.5625` | Player-Breite/Höhe (Standard 9:16); reine Zoommetadaten |
| `--ffmpeg 'C:\Programme\ffmpeg.exe'` | Eigenes FFmpeg statt gebündelter Version; libx264, `-fps_mode` und `-enc_time_base:v demux` erforderlich |
| `--overwrite` | Vorhandenes Paket nach erfolgreicher Analyse atomar ersetzen |

Fortschritt erscheint auf stderr; Ergebnis/Qualitätswarnungen auf stdout.
Exitcodes: 0 = gültiger Export, auch bei `partial`; 1 = Import-/Modell-/Datei-/
Validierungsfehler; 2 = ungültige CLI-Syntax; 130 = Abbruch. Ein Video ohne
erkannte Person wird als `partial` mit 33 fehlenden Gelenken je Frame
exportiert, nicht als erfolgreiche Körpererkennung bezeichnet.

## Zeitbezug, Medien und Ressourcen

FFmpeg normalisiert erste Video-/optionale erste Audiospur auf MP4/H.264/
yuv420p und AAC, wendet Orientierung physisch an und entfernt andere Spuren/
Metadaten. `-copyts -start_at_zero -fps_mode passthrough` erhält variable
Frameabstände; `-enc_time_base:v demux` erhält auch Zeitpunkte zwischen den
nominalen FPS-Rasterpunkten. Der gemeinsame Containerstart wird auf null bezogen, relative
A/V-Abstände bleiben erhalten. Keine Kürzung, Beschleunigung oder Spiegelung.
`audio.offsetSeconds=0`, da Verzögerungen im eingebetteten Ton liegen.
AAC-Neukodierung kann die technische Startmarke um einen Audioframe verschieben;
der VFR-/Audiotest prüft 30 ms Toleranz. Ungerade H.264-Abmessungen werden mit
FFmpeg-Fehler abgewiesen, statt stillschweigend Bildgeometrie zu ändern.
Nichtquadratische Videopixel werden ebenfalls ausdrücklich abgewiesen.
Eine fehlende Angabe zum Pixelseitenverhältnis (`None` oder `0/1`) ist zulässig:
Sie wird als quadratische Pixel behandelt und im Paketvideo explizit als `1/1`
gespeichert, ohne die Bildabmessungen zu verändern.

Analysiert wird das normalisierte Paketvideo. Exportzeiten sind
`frame.pts * frame.time_base` (Float64), niemals Frameindex/FPS oder Laufzeit.
Fehlende, negative oder nicht streng steigende PTS brechen ab. Nur die
MediaPipe-Uhr erhält streng steigende ganzzahlige Millisekunden; exportierte
Sekunden werden nicht gerundet. Weltwerte werden um den Hüftmittelpunkt
zentriert. Ungültige/fehlende Werte ergeben fünf NaN und zwei Nullen;
Presence wird niemals durch Visibility ersetzt.

Jeweils ein Frame wird verarbeitet; Posen/Zeiten gehen direkt auf Disk.
Zwei Decoder-/Encoderthreads, keine Segmentierung, keine Sammlung aller Frames
im Speicher. Limits: 4 Stunden, 1 Million Analyseframes, maximal 4096×2160
Pixel insgesamt pro Videobild, 900 MiB normalisiertes Video und 1 GiB Paket.
Grenzen führen zum Abbruch, nicht zu gekürzten Exporten. FFmpeg-Zeitlimit:
4 Stunden. Temporäre Dateien liegen im Ausgabeordner; bis etwa 2 GiB freien
Platz zusätzlich zur Quelle vorsehen. CPU-Inferenz kann länger als das Video
dauern. SHA-256 und ZIP-Ausgabe erfolgen ebenfalls blockweise. Der unveränderte
Paketprüfvertrag wird vor Veröffentlichung der Ausgabedatei vollständig geprüft.

## Qualität, Zoom und Grenzen

`quality.json` enthält ausschließlich die drei Schemafelder `status`,
`missingLandmarks`, `warnings`. `complete` bedeutet nur „kein fehlendes Gelenk“.
Geringe Konfidenz, Mehrpersonenbilder, Bildrandnähe, fehlende Gelenke und
Zeitlücken über 0,5 s werden mit Anzahl und erstem/letztem betroffenem Zeitpunkt
zusammengefasst. Diese Spanne ist kein durchgehendes Fehlerintervall.

Ein fester Zoom umfasst die Grenzen aller zuverlässigen 33-Punkte-Posen über
die komplette Choreografie, mit 8 % Reserve und weiteren 5 % oberhalb des
Kopfes. Zum Zielseitenverhältnis wird nur erweitert, gegebenenfalls mit Balken.
Bei einem unsicheren Frame, Bildrandnähe oder zeitlichem Sampling gilt
Ganzbild mit Warnung. Video, Posen und Zeitstempel werden nicht zugeschnitten.

Voraussetzung: **eine vorgesehene Person im Video**. MediaPipe sucht bis zu
zwei Posen; bei mehreren erkannten Personen wird der ganze Frame fehlend
geschrieben. Noch keine Personenauswahl oder Identitätsverfolgung. Nicht
erkannte Nebenpersonen und Identitätswechsel zwischen Einzelpersonen lassen
sich nicht ausschließen. Mehrpersonenaufnahmen erfordern einen Folgeauftrag.
3D ist eine hüftrelative Modellschätzung, kein kalibriertes Motion Capture.
Tanzclips mit Drehungen/Verdeckungen und Langzeitperformance bleiben manuell
abzunehmen.

## Prüfung

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -p test_analyzer.py -v
.\.venv\Scripts\python -m unittest discover -s tests -p test_choreo.py -v
.\.venv\Scripts\python -m analyzer.validate tests/fixtures/synthetic.choreo
node tests/zoom.test.cjs
```

Analyzertests erzeugen lokale synthetische Videos; reproduzierbare Posefälle
verwenden einen ausdrücklich synthetischen Engine-Stub. Kein Modelldownload
im Testlauf. Echte MediaPipe-Smoke-Tests und offene Abnahmen:
[TEST_RESULTS.md](../docs/TEST_RESULTS.md). Windows-CI prüft Python 3.12/3.13,
ohne Deployment. Bestehende Browsertests: Root-README.

CC0-Fixture neu erzeugen: FFmpeg im PATH und `python -m analyzer.create_example`.
Dieser bestehende Generator ist unabhängig vom CLI-Export. Schema und Fixture
bleiben unverändert. [FORMAT.md](../shared/FORMAT.md) und
[VALIDATION.md](../shared/VALIDATION.md) sind verbindlich.

Grundlagen: [MediaPipe Pose Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python),
[Delegates](https://ai.google.dev/edge/mediapipe/solutions/setup_python),
[PyAV-PTS und Zeitbasen](https://pyav.org/docs/stable/api/time.html).
