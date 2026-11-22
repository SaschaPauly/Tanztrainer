# Showtanz-Analyzer – Phase 2 und 3

Eigenständige lokale Windows-Python-CLI: Video importieren, MediaPipe Pose
Landmarker mit 33 Punkten ausführen und ein validiertes `showtanz-choreo 1.0.0`
schreiben. Phase 3 ergänzt eine native Windows-Oberfläche mit Prüfung vor dem
Speichern. Phase 4 ergänzt den lokalen `.choreo`-Import im Tanztrainer:
[Browser-Bedienung und Limits](../docs/CHOREO_BROWSER.md). CLI, GUI und
Dateiformat bleiben dabei unverändert.

## Windows-Oberfläche: Einrichtung und Start

Python 3.12 oder 3.13 (64 Bit) und eine vorhandene `.venv` vorausgesetzt:

```powershell
.\.venv\Scripts\python -m pip install -r analyzer/requirements-gui.txt
.\.venv\Scripts\python -m analyzer.gui
```

Danach genügt ein Doppelklick auf **`Showtanz-Analyzer.cmd`** in der
Repositorywurzel. Das Fenster startet ohne Konsole. Bei Startproblemen den
obigen Python-Befehl in PowerShell verwenden, um die Fehlermeldung zu sehen.
Es ist eine Python-Desktopanwendung; ein eigenständig gebündelter EXE-Installer
ist nicht Bestandteil dieser Phase. Die zusätzlichen Qt-Pakete sind groß;
die bestehende CLI benötigt sie weiterhin nicht.

### Bedienung

1. **Video importieren**: lokale Datei wählen. Der Import bereitet H.264/AAC
   im Hintergrund vor; Originaldatei bleibt erhalten. Das erste Bild erscheint
   stumm und pausiert. Abspielen/Pause und Zeitleiste dienen zur Sichtprüfung.
2. Unter **Lokales Modell** Lite wählen; Standard ist
   `models/pose_landmarker_lite.task`. Falls es fehlt, lädt ausschließlich der
   ausdrücklich betätigte Button **Lite-Modell von Google herunterladen** das
   versionierte Google-Bundle. Keine Modell-/Videodownloads beim Programmstart.
3. **Auf dem Video ist nur eine Person sichtbar** nur bestätigen, wenn dies
   für die gesamte Aufnahme gilt. Optional **Person am Videoanfang markieren**
   aktivieren und im ersten Bild auf die Mitte zwischen Schultern und Hüfte
   klicken. Währenddessen bleibt die Wiedergabe gesperrt; erneut ausschalten
   entfernt die Markierung. Die Auswahl ist ein heuristischer Startanker,
   keine garantierte Identitätserkennung. Nach längerer Lücke wird bei einer
   markierten Person nicht ungeprüft zur größten anderen Figur gewechselt.
4. **Analyse starten**. Standard: Lite (sofern als Modell gewählt), CPU,
   alle Bilder, Analyse-Bildkante 1280, 30 % Zoomtoleranz und die bestehende
   getrennte Rumpf-/Verdeckungszeitregel. Weitere Einstellungen bewusst
   freischalten. Zeitliche Abtastung reduziert Rechenarbeit, erzwingt aber
   weiterhin Ganzbild. GPU/auto nutzen den vorhandenen CPU-Fallback.
5. **Prüfen**: Video mit farbigen Haltungspunkten ansehen; **Fester Zoom**
   und **Haltungspunkte** lassen sich unabhängig umschalten. Grün ≥ 0,65,
   Gelb ≥ 0,5, Rot < 0,5 (Minimum aus Visibility und Presence). Fehlende
   Punkte bleiben unsichtbar; es werden keine Werte erfunden/interpoliert.
   Einzelbildbuttons dekodieren exakt den gespeicherten Videotimestamp im
   Hintergrund; normale Wiedergabe ordnet Posen am dekodierten Frame-PTS zu.
   Warnungen, fehlende Punkte, Toleranz und Ganzbild-Fallback im Bericht lesen.
6. **.choreo speichern**: erst jetzt Ziel wählen. Vollständige Prüfung und
   atomare Veröffentlichung schützen vor unvollständigen Paketen. Der normale
   Windows-Speicherdialog fragt vor dem Ersetzen einer bestehenden Datei.
   Ein bereits geöffnetes Paket bitte unter anderem Namen speichern.
7. Optional **Haltungspunkte als CSV / SQLite ausgeben**: einen **neuen**
   Ordnernamen wählen. CSV, SQLite und Bericht enthalten dieselben 2D- und
   geschätzten hüftrelativen 3D-Werte; keine erneute Analyse.

Mit **.choreo öffnen** kann auch das bereits erstellte Lite-Ergebnis direkt
geprüft werden. Dabei sind weder Modell noch Originalvideo erforderlich.
Der Titel und die Einstellungen gelten für neue Analysen; beim Speichern
eines geöffneten Pakets werden dessen Metadaten unverändert übernommen.

**Abbrechen** fordert einen kooperativen Abbruch an. Ein laufender einzelner
Modell-/Prüfschritt wird noch beendet; beim Modelldownload kann die Netzwerk-
Zeitüberschreitung bis 60 s benötigen. Schließen während eines Auftrags fordert
ebenfalls Abbruch an und wartet auf Ressourcenfreigabe. Temporäre Videokopien
liegen im lokalen Windows-Temp-Ordner und werden bei regulärem Abschluss/
Schließen entfernt; ein Prozessabsturz kann temporäre Dateien hinterlassen.
Genügend freien lokalen Speicher für Originalkopie, Ergebnis und Vorschau
einplanen. Auf fehlende Windows-Codecs/Audioausgabe weist die Vorschau hin;
erfolgreiche automatisierte Tests ersetzen keine Prüfung anderer PCs.

Automatische GUI-Prüfung (ohne Netzwerk/Modell):

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -p test_gui_backend.py -v
.\.venv\Scripts\python -m unittest discover -s tests -p test_gui.py -v
```

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
| `--zoom-max-uncertain-percent 30` | Anteil unsicherer Analysebilder für festen Zoom; Standard 30 %, einschließlich der Grenze. 0 stellt die strenge Regel wieder her |
| `--ffmpeg 'C:\Programme\ffmpeg.exe'` | Eigenes FFmpeg statt gebündelter Version; libx264, `-fps_mode` und `-enc_time_base:v demux` erforderlich |
| `--overwrite` | Vorhandenes Paket nach erfolgreicher Analyse atomar ersetzen |
| `--single-person` | Nach ausdrücklicher Bestätigung einer Einpersonenaufnahme: Vordergrundfigur zeitlich verfolgen, Zusatzdetektionen konservativ behandeln |
| `--target-point 0.5,0.5` | Optionaler Startanker am Oberkörper im ersten Bild; normiertes X,Y im ganzen Originalbild; aktiviert konservative Personenauswahl |

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
Bis einschließlich **30 % unsichere Analysebilder** sind standardmäßig
zulässig. Ein Bild zählt einmal als unsicher, wenn Punkte fehlen, mindestens
eine Konfidenz unter 0,5 liegt oder die Personenzuordnung nicht eindeutig ist.
Die Prozentzahl bezieht sich auf Bilder, nicht auf Gelenke, Videodauer oder
einen erlaubten Koordinatenfehler. Mehrere Probleme im selben Bild zählen
zusammen als ein unsicheres Bild. Alle zuverlässigen Punkte aus diesen Bildern
bleiben in der Bewegungsvereinigung enthalten; es werden keine Extrema getrimmt.
Bei tolerierten unsicheren Bildern kommen weitere 5 % Randreserve dazu.

Die Zeitregel unterscheidet **Teilunsicherheit** von **Kern-/Zuordnungsverlust**:
Sind mindestens drei der vier Schulter-/Hüftpunkte (11, 12, 23, 24) mit
Visibility und Presence ab 0,5 vorhanden und ist eine Person zugeordnet,
dürfen einzelne Gelenke auch länger als 0,5 s unsicher bleiben. Diese Bilder
zählen weiterhin vollständig zum 30-%-Budget. Fehlt diese Rumpfbasis oder ist
die Zuordnung unklar, läuft eine eigene Uhr; über 0,5 s führt sie zum Ganzbild.
Benachbarte Finger-/Gelenkverdeckungen verlängern diese Kernlücke nicht.

Über 30 %, bei einer zusammenhängenden Rumpf-/Zuordnungslücke über 0,5 s,
Bildrandnähe, echten Zeitlücken über 0,5 s oder zeitlichem Sampling gilt
weiterhin Ganzbild mit Warnung. Lückendauern umfassen die begrenzenden
zuverlässigen Zeitpunkte, soweit vorhanden. `--zoom-max-uncertain-percent` erlaubt eine
explizite andere Grenze von 0 bis 100; Sicherheitsgrenzen und fehlende
Bewegungsdaten bleiben wirksam. Nicht beobachtete Bewegungen können trotz
Randreserve außerhalb des Ausschnitts liegen. Posen und Zeitstempel bleiben
unverändert, es gibt keine Interpolation oder physische Videobeschneidung.

Voraussetzung: **eine vorgesehene Person im Video**. MediaPipe sucht bis zu
zwei Posen. Standardmäßig wird bei mehreren Erkennungen der ganze Frame
fehlend geschrieben. `--single-person` ist nur für ausdrücklich bestätigte
Einpersonenaufnahmen gedacht: Eine deutlich größere Vordergrundfigur wird
initial gewählt, danach werden Position und Größenänderung über die Zeit
verglichen. Bei ähnlichen Kandidaten oder Positionssprüngen bleibt die Pose
fehlend. Nach mehr als 0,75 s ohne sichere Zuordnung ist eine konservative
Neuauswahl nötig und wird dokumentiert. Das ist keine garantierte
Identitätsverfolgung oder automatische Spiegelungserkennung. Die Auswahl muss
in der Vorschau kontrolliert werden. Mehrpersonenaufnahmen bleiben Folgearbeit.
3D ist eine hüftrelative Modellschätzung, kein kalibriertes Motion Capture.
Tanzclips mit Drehungen/Verdeckungen und Langzeitperformance bleiben manuell
abzunehmen.

## Skelettvorschau und Lite/Full/Heavy vergleichen

Die drei offiziellen Google-Modelle werden nur nach ausdrücklichem Aufruf
heruntergeladen. Bestehende lokale `.task`-Dateien können wiederverwendet werden:

```powershell
.\.venv\Scripts\python -m analyzer.models models
.\.venv\Scripts\python -m analyzer.compare_models 'C:\Tanzvideos\Training.mp4' 'C:\Tanzvideos\Training - Modellvergleich' --models-dir models --single-person --backend cpu
```

Der neue Ausgabeordner enthält `vergleich.html`, `reference.mp4`, drei gültige
Pakete `lite.choreo`, `full.choreo`, `heavy.choreo`, `vergleich.json` und
`bildervergleich.csv`. `vergleich.html` per Doppelklick in Chrome oder Edge
öffnen. Alle Dateien zusammen im selben Ordner belassen. Keine Serverinstallation,
kein Browser-Modell, kein CDN und keine Netzwerkanfragen in der Vorschau.

Bedienung: gemeinsame Wiedergabe/Zeitleiste, voriges/nächstes Analysebild,
Einzelmodell bei „Darstellung“ groß anzeigen,
Ton, zusätzliche Erkennungen und Punktnummern ein-/ausblenden. Drei Ansichten
zeigen denselben Videotimestamp mit farbigem Skelett: Grün ab 0,65, Gelb ab
0,50, Rot unter 0,50 (jeweils Minimum aus Visibility und Presence). Fehlende
Punkte werden nicht erfunden. Weiß umrahmt die gewählte Figur, Grau zeigt
zusätzliche Modellhypothesen. Diese können Spiegelungen oder Fehlkennungen
sein; eine reale zweite Person wird daraus nicht abgeleitet. Türkis markiert
den festen Zoomrahmen; „Festen Zoom anwenden“ stellt den Crop mit nötigen
Balken dar. Das Originalvideo wird nicht verändert.

Die Messwerte trennen unsichere Bilder über alle 33 Punkte von der Abdeckung
der acht Arm-/Beinabschnitte. Als verwertbar zählt hier mindestens sechs von
acht Abschnitten mit Visibility und Presence ab 0,65 an beiden Endpunkten.
Das ist eine Diagnose der Referenz, keine Trainingsnote und keine gemessene
Genauigkeit. Geringere Unsicherheit allein beweist keine bessere Pose.
Modellidentität inklusive SHA-256, Qualitätswarnungen, tatsächliche Auswahl,
Zusatzdetektionen und gesamte Verarbeitungszeit stehen in den Vergleichsdaten.
`selectedIndex` ist in CSV/JSON nullbasiert (leer/null bei keiner Auswahl);
die Vorschau zeigt die Figuren zur leichteren Bedienung als 1 und 2 an.

Standardmäßig werden alle Bilder sequenziell auf CPU analysiert. Dieselben
PTS sind für alle drei Modelle verbindlich; Abweichungen brechen den Vergleich
ab. `--max-fps 10` erlaubt einen ausdrücklich gekennzeichneten Stichprobentest;
das aktiviert wie bisher den Ganzbild-Zoom-Fallback. `--max-side` begrenzt die
Inferenzauflösung für alle Modelle gleich. Die Vorschau ist auf 20000
Analysezeitpunkte begrenzt; für längere Videos eine niedrigere Abtastrate
wählen. Unterbrochene/fehlgeschlagene Vergleiche veröffentlichen keinen
unvollständigen Ergebnisordner. Die drei Analysen können mehrere Minuten
dauern; Speicherplatz für drei Pakete plus Vorschauvideo vorsehen.

`--download-models` beim Vergleich ist eine alternative ausdrückliche
Downloadfreigabe für die Google-Modelle. Die eigentliche Analyse überträgt
keine Bilder, Posen oder Videos. Modelle und persönliche Ergebnisse nicht
einchecken. Ein fehlendes Modell führt ohne Downloadoption zum Fehler.

## Haltungspunkte separat für Tests ausgeben

Ein vorhandenes, gültiges Paket kann ohne neue Videoanalyse lesbar exportiert
werden. Der Ausgabeordner muss neu sein; sein übergeordneter Ordner existiert:

```powershell
.\.venv\Scripts\python -m analyzer.export_poses 'C:\Tanzvideos\Training.choreo' 'C:\Tanzvideos\Training - Haltungspunkte'
```

- `haltungspunkte.csv`: 33 Zeilen pro Analysezeitpunkt, mit Frameindex,
  Originaltimestamp, Gelenkindex/-name, Bild-X/Y, geschätztem Welt-X/Y/Z,
  Visibility, Presence und Missing-Kennzeichen.
- `bilder.csv`: eine Zeile pro Analysezeitpunkt mit Fehlzahl, Anzahl vorhandener
  Punkte mit Konfidenz unter 0,5 und zuverlässigen Punkten nahe dem Bildrand.
- `haltungspunkte.sqlite`: Tabellen `frames`, `landmarks`, `landmark_names`,
  `metadata`; Ansicht `pose_points` verknüpft Zeitpunkte, Namen und Punkte.
- `bericht.json`: Manifest/Qualitätsbericht, berechnete Fehlzahlen und Zoomstatus.
- `LIESMICH.txt`: Erläuterung der Koordinaten und Dateien.

CSV verwendet UTF-8 mit BOM, Semikolon und Dezimalkomma für deutsches Excel.
SQLite speichert Zahlen direkt als REAL. Fehlende Koordinaten sind leere
CSV-Zellen bzw. SQL-NULL, niemals erfundene Nullen. Alle Frame-/Gelenkindizes
beginnen bei 0. Für die Datenprüfung reicht die Validator-Abhängigkeit
`analyzer/requirements.txt`; MediaPipe, FFmpeg und ein Modell sind nicht nötig.
Das Quellpaket bleibt unverändert. Daten werden frameweise aus dem validierten
Paket gelesen; es findet keine neue Modellerkennung oder Interpolation statt.
Die Dateien enthalten die lokalen Bewegungsdaten und gehören nicht ins
öffentliche Git-Repository.

Zoomdiagnose: Der Algorithmus toleriert standardmäßig bis zu 30 % unsichere
Analysebilder. Anteil, Grenze und getrennte Teil-/Kernlücken stehen in den Warnungen.
Er verändert das Video auch bei
einem berechneten Crop nicht physisch; die Zoommetadaten muss später der Player
anwenden. Niedrige Konfidenzen sind in den Punkttabellen erkennbar. Die Zahl
erkannter Personen wurde im Format 1.0.0 nicht pro Frame gespeichert und kann
aus dem Export nicht nachträglich rekonstruiert werden; dafür bleiben die
zusammengefassten Warnungen im ursprünglichen Qualitätsbericht maßgeblich.

## Zoom vorhandener Pakete ohne neue Modellerkennung berechnen

```powershell
.\.venv\Scripts\python -m analyzer.rezoom 'C:\Tanzvideos\Training.choreo' 'C:\Tanzvideos\Training - Zoom30.choreo'
```

Schreibt eine neue Datei mit aktueller Zoomregel. Das Quellpaket wird nicht
überschrieben; Video, Posen, Zeitstempel, Vorschau und Audiooffset bleiben
unverändert. Nur Zoom, Qualitätsbericht und zugehörige Manifest-/Hashwerte
ändern sich. Hashes/Schema werden vorab und beim Export vollständig geprüft.
Die Videoframes werden einmal mit PyAV dekodiert, um vollständige zeitliche
Abdeckung zu prüfen; bei fehlenden Analysezeitpunkten bleibt der Zoom Ganzbild.
Kein MediaPipe-Lauf und kein Modelldownload nötig. Alte Zoommeldungen werden
durch aktuelle Befunde ersetzt, andere Qualitätswarnungen bleiben erhalten.
Im v1-Format sind unzugeordnete Posen vollständig fehlend; sie gelten bei der
Neuberechnung konservativ als verlorene Körperbasis. Die Personenauswahl wird
nicht neu durchgeführt. Eine bestehende HTML-Vorschau muss separat mit den
neuen Paketen erzeugt werden, da sie eine unveränderliche Datensicht enthält.

## Prüfung

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -p test_analyzer.py -v
.\.venv\Scripts\python -m unittest discover -s tests -p test_choreo.py -v
.\.venv\Scripts\python -m unittest discover -s tests -p test_export_poses.py -v
.\.venv\Scripts\python -m unittest discover -s tests -p test_model_comparison.py -v
.\.venv\Scripts\python -m unittest discover -s tests -p test_zoom_policy.py -v
node tests/preview.test.cjs
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
