# showtanz-choreo 1.0.0 (verbindlich)

`.choreo` ist ein lokales, portables ZIP-Paket einer einzigen ausgewählten Person.
Es enthält genau sieben reguläre Dateien, keine Verzeichniseinträge und keine
weiteren Dateien. Groß-/Kleinschreibung ist verbindlich. Alle JSON-Dateien sind
UTF-8 ohne BOM, mit eindeutigen Schlüsseln, ohne NaN/Infinity. Das Manifest folgt
[choreography.schema.json](choreography.schema.json), Draft 2020-12; zusätzliche
Manifestfelder sind verboten. Unbekannte Versionen werden abgewiesen, niemals
stillschweigend konvertiert. Dateinamen bleiben versionsübergreifend reserviert.

| Pfad | Verbindlicher Inhalt |
| --- | --- |
| `manifest.json` | Metadaten und Integritätsverzeichnis laut Schema |
| `reference/video.mp4` | Originale, ungespiegelte Videotimeline ab 0 s; MP4, H.264/AVC, yuv420p, optional AAC; keine zeitliche Kürzung oder Beschleunigung; Orientierung physisch aufrecht, keine Rotation über Metadaten |
| `reference/poses.bin` | Headerlose frameweise Pose-Datensätze |
| `reference/timestamps.bin` | Headerlos ein Float64 je Pose, in Sekunden |
| `reference/zoom.json` | Exakt dasselbe JSON-Objekt wie `manifest.zoom` |
| `reference/quality.json` | Qualitätszusammenfassung, siehe unten |
| `assets/preview.jpg` | Eigenständig dekodierbares JPEG, Vorschau ohne Orientierungsmetadaten |

Der Analyzer darf das Video zur Codec-Kompatibilität transkodieren, muss dabei
Bildgeometrie, Originaltimeline und Tonversatz erhalten. `video.width/height`
bezeichnen die tatsächlichen Pixelabmessungen dieser aufrechten Datei. Das
spätere Analysemodell arbeitet auf diesem Bild. Weitere Tondateien sind in v1
nicht zulässig. Codec- und Decoderprüfung ist zusätzlich zum Paketvalidator
bei Medienimport erforderlich; der Validator prüft lediglich Dateisignaturen,
keine vollständigen MP4-/JPEG-Bitstreams oder reale Modellplausibilität.

## Manifest

- `format`: exakt `showtanz-choreo`; `version`: exakt `1.0.0`.
- `title`: nichtleerer Unicode-Text, maximal 200 Zeichen; als Text anzeigen,
  niemals als HTML interpretieren.
- `durationSeconds`: positive Videodauer in Sekunden, höchstens 14.400.
- `frameCount`: Anzahl gespeicherter Analysezeitpunkte (nicht Videoframes),
  ganzzahlig 1 bis 1.000.000. Keine konstante Abtastrate voraussetzen.
- `model.name/version`: nichtleere genaue Identifikation des verwendeten Modells
  bzw. der synthetischen Quelle; Modellversion ist kein Formatversionsalias.
- `coordinateSystem`, `layout`: feste Schema-Konstanten; keine alternativen
  Layouts in dieser Version.
- `video.width/height`: positive ganze Pixelzahlen, höchstens 16.384 je Achse.
- `zoom`: fester Ausschnitt und bevorzugtes Player-Seitenverhältnis, siehe unten.
- `audio.source`: `reference/video.mp4` für dessen eingebettete Tonspur oder
  `none` für stumm. `offsetSeconds`: endlich, ±14.400 s. Zur Videoposition `t`
  gehört Audiozeit `t - offsetSeconds`; positiv bedeutet später einsetzenden
  Ton. Negative Audiozeiten sind Stille. Bei `none` ist der Offset ohne Wirkung.
  Für synchronen Originalton 0 verwenden; Offset verändert keine Posezeiten.
- `files`: genau sechs Nutzdateipfade als Schlüssel, jeweils `size` als positive
  ganze Anzahl unkomprimierter Bytes und `sha256` als 64 kleine Hexzeichen des
  gesamten unveränderten Dateiinhalts. Auch Zoom und Qualität sind gehasht.
  `manifest.json` ist durch seine feste Position referenziert und hat bewusst
  keinen Selbsthash (Zirkularität); ZIP-Größe/CRC werden unabhängig geprüft.
  SHA-256 ist Integritätsprüfung, keine Authentizitäts- oder Vertrauensgarantie.

Alle Zahlen im JSON sind endlich. Weitere konkrete Grenzwerte und Feldtypen
sind im Schema verbindlich festgelegt.

## Binärlayout und Gelenke

IEEE-754, **Little Endian**, keine Header, kein Padding. Für Frame `f`, Gelenk
`j` und Feld `k` liegt Float32 bei Byte `(f * 231 + j * 7 + k) * 4`.
Pro Frame 33 × 7 × 4 = **924 Byte**. Länge exakt `frameCount * 924`.

| k | Wert | Definition |
| --- | --- | --- |
| 0 | imageX | X / Originalbildbreite, [0,1], links nach rechts |
| 1 | imageY | Y / Originalbildhöhe, [0,1], oben nach unten |
| 2 | worldX | Modellgeschätzte Meter, positiv nach Bildrechts |
| 3 | worldY | Modellgeschätzte Meter, positiv nach unten |
| 4 | worldZ | Modellgeschätzte Meter, positiv von der Kamera weg |
| 5 | visibility | Modellwahrscheinlichkeit für Sichtbarkeit, [0,1] |
| 6 | presence | Modellwahrscheinlichkeit für Vorhandensein, [0,1] |

Bildursprung ist die linke obere Kante des **gesamten aufrechten, ungespiegelten
Originalvideos**; rechte/untere Kante ist 1. Kein Crop-, Player- oder
Kameraspiegel-Koordinatensystem. Kein Bild-Z wird gespeichert. Weltursprung ist
pro Pose der Mittelpunkt zwischen den Hüftgelenken; X/Y/Z wie MediaPipe Pose
World Landmarks, ohne Drehung, Kamera-Kalibrierung oder globale Translation.
Weltwerte sind Schätzungen, keine vermessenen Bühnenpositionen. Anatomische
links/rechts bleiben erhalten, auch wenn die Person sich dreht.

Reihenfolge ist MediaPipe Pose 33 (nullbasiert), maschinenlesbar in
[landmarks.json](landmarks.json):

```text
 0 nose                 1 left_eye_inner        2 left_eye
 3 left_eye_outer       4 right_eye_inner       5 right_eye
 6 right_eye_outer      7 left_ear              8 right_ear
 9 mouth_left          10 mouth_right          11 left_shoulder
12 right_shoulder      13 left_elbow           14 right_elbow
15 left_wrist          16 right_wrist          17 left_pinky
18 right_pinky         19 left_index           20 right_index
21 left_thumb          22 right_thumb          23 left_hip
24 right_hip           25 left_knee            26 right_knee
27 left_ankle          28 right_ankle          29 left_heel
30 right_heel          31 left_foot_index      32 right_foot_index
```

Fehlendes Gelenk: alle fünf Koordinaten IEEE quiet NaN, visibility und presence
exakt 0. Autoren sollen das kanonische Float32-Bitmuster `0x7fc00000` schreiben;
Leser akzeptieren alle NaN-Bitmuster. Teilweise NaN, Infinity und erfundene
Nullkoordinaten sind verboten. Fehlen Weltwerte, eine der beiden
Wahrscheinlichkeiten oder liegen Bildkoordinaten außerhalb [0,1], muss das
**gesamte Gelenk als fehlend** geschrieben werden (nicht an Bildkanten klemmen).
Niedrige endliche Wahrscheinlichkeiten dürfen unverändert gespeichert werden.
Bei fehlender Person werden alle 33 Gelenke fehlend, der Zeitstempel bleibt.
Keine automatische Interpolation, keine 0,0-Platzhalter, keine stillschweigende
Ersetzung von Presence durch Visibility.

`timestamps.bin`: IEEE Float64 Little Endian, Byteoffset `f * 8`, Länge exakt
`frameCount * 8`. Endlich, >=0, streng monoton steigend und <= Videodauer;
Original-Videotimeline in Sekunden, keine Wallclock und keine Laufzeit seit
Analysestart. Der erste Wert muss nicht 0 sein. Zeitlücken sind erlaubt.

`quality.json` hat ausschließlich `status` (`complete` bei keinem fehlenden
Gelenk, sonst `partial`), `missingLandmarks` (ganze Zahl 0 bis frameCount × 33)
und `warnings` (höchstens 100 Strings mit jeweils höchstens 500 Zeichen).
Die Fehlzahl zählt Gelenke über alle Frames, nicht unzuverlässige Konfidenzen.

## Fester Zoom und CSS

`mode` ist `fixed`. `x,y,width,height` sind normalisierte Originalbildwerte.
`x,y >= 0`, `width,height > 0`, `x+width <= 1`, `y+height <= 1`;
`targetAspectRatio > 0` ist Playerbreite / Playerhöhe. Keine Animation,
kein per-Frame-Zoom und kein Einfluss auf gespeicherte Posen oder Zeitstempel.

Späterer Analyzer: über alle Zeitpunkte konservative Ganzkörpergrenzen mit
Sicherheitsreserve bestimmen; Hände, Füße und Kopf haben Vorrang. Bei
unsicheren Grenzen Originalbild `(0,0,1,1)` benutzen und Warnung hinterlegen.
Den Rahmen zum Zielseitenverhältnis **erweitern**, niemals zur Vergrößerung
abschneiden. Reicht das Originalbild dafür nicht aus, Balken zulassen. Selbst
Ganzbild kann außerhalb des Videos abgeschnittene Körperteile nicht ergänzen.
In Phase 1 wird dieser Analysealgorithmus noch nicht implementiert.

Für Originalgröße `W,H`, Ausschnitt `x,y,w,h` und Player-Innenfläche `Pw,Ph`:

```js
const cropW = w * W, cropH = h * H;
const scale = Math.min(Pw / cropW, Ph / cropH);
const left = (Pw - cropW * scale) / 2 - x * W * scale;
const top  = (Ph - cropH * scale) / 2 - y * H * scale;
// Video absolut im Player: width=W*scale px, height=H*scale px,
// left=left px, top=top px, max-width:none; keine weitere object-fit-Skalierung.
```

Damit außerhalb des Ausschnitts keine weiteren Videobereiche in den Balken
sichtbar werden: mittig eine Clipfläche der Größe `cropW*scale` × `cropH*scale`
anlegen (`overflow:hidden`), Video darin um `-x*W*scale,-y*H*scale` versetzen.
Der äußere Player hat schwarzen Hintergrund und `aspect-ratio:
targetAspectRatio`. Bei abweichender Playergröße obige Rechnung wiederholen.
Das komplette Crop bleibt sichtbar; `object-fit:cover` wäre dafür ungeeignet.

## Sicherheit und Kompatibilität

[VALIDATION.md](VALIDATION.md) ist die normative sprachunabhängige
Validierungsspezifikation; [validation-spec.json](validation-spec.json) enthält
gemeinsame Limits und Dateiliste. Der Python-Validator implementiert diese
Prüfungen. ZIP wird nie auf Disk extrahiert. Inhalte erst nach vollständigem
Erfolg an Decoder oder spätere Auswertung übergeben. Keine Netzwerkreferenzen,
Cloud-Dienste oder ausführbaren Paketbestandteile.
