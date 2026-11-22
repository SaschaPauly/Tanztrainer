# Validierungsvertrag für Python und JavaScript

Normativ für showtanz-choreo 1.0.0. Alle Implementierungen müssen Schema **und**
Semantik prüfen. Ein JSON-Schema allein validiert keine ZIP- oder Binärdaten.
Fehler enthalten Dateiname/Feld und eine verständliche Ursache. Unbekannte
Versionen ablehnen. Keine Teilfreigabe beschädigter Pakete.

1. Vor ZIP-Parsing Archivgröße <= 1.073.741.824 Bytes prüfen. EOCD in den letzten
   65.557 Bytes finden; Kommentarende muss exakt Archivende sein. Nur ein Disk,
   gleiche Eintragszahl auf Disk und insgesamt, höchstens 7. ZIP64/Multipart
   nicht unterstützt. Zentralverzeichnis <= 65.536 Bytes und direkt vor EOCD.
   Damit keine riesige Eintragsliste allein durch Parserinitialisierung entsteht.
2. Genau die sieben Pfade aus `validation-spec.json`, keine doppelten Namen,
   NUL, Verzeichnisse, Symlinks, Geräte, absoluten/Drive-/Backslash-/Traversal-
   oder zusätzlichen Pfade. Nicht normalisieren und danach akzeptieren: nur
   exakter Allowlist-Vergleich. ZIP-Pfade aus lokalen und zentralen Headern
   müssen übereinstimmen; CRC, Header und überlappende Einträge prüfen.
3. Nur STORE (0) oder DEFLATE (8), keine Verschlüsselung. Je Eintrag positive
   unkomprimierte Größe <= 1.073.741.824; Summe <= 1.610.612.736 Bytes;
   JSON jeweils <= 1.048.576 Bytes. Verhältnis unkomprimiert / max(1,komprimiert)
   <= 100. Limits vor dem Dekomprimieren prüfen; tatsächliche Ausgabe während
   Streaming mitzählen und bei Überschreiten der deklarierten Größe oder des
   Limits abbrechen. Ausgabe muss am Ende exakt deklarierter Größe entsprechen.
   Konsumenten dürfen strengere Limits setzen (insbesondere mobile Browser).
4. JSON streng als UTF-8 lesen, doppelte Schlüssel und NaN/Infinity ablehnen.
   Manifest nach Draft 2020-12 validieren, z.B. mit Ajv 2020 (strictNumbers,
   keine Typumwandlung, keine automatische Default-/Additional-Property-Änderung).
   JavaScript `JSON.parse` erkennt doppelte Schlüssel **nicht**: vorher einen
   JSON-Tokenizer/Parser mit Duplicate-Key-Prüfung verwenden. Verschachtelungs-
   oder Parserressourcenfehler als ungültige Eingabe behandeln.
5. Für sechs Nutzdateien unkomprimierte Länge und vollständigen SHA-256 gegen
   Manifest prüfen, CRC unabhängig über ZIP-Leser prüfen. Keine Selbstprüfsumme
   des Manifests. SHA-256 nach Bytes, nicht nach neu serialisiertem JSON.
6. Binärlängen exakt `frameCount*924` und `frameCount*8`. Alle Regeln zu
   Zeitstempeln, Koordinaten, fehlenden Werten und Konfidenzen aus FORMAT.md
   prüfen, einschließlich frameübergreifender Zeitreihenfolge.
7. Zoomobjekt strukturell (nicht anhand JSON-Textformatierung) mit Manifest
   vergleichen; Rechteckgrenzen prüfen. quality.json exakt drei Felder und
   Typen/Grenzen aus FORMAT.md; Fehlzahl und Status gegen Binärdaten prüfen.
8. MP4: Bytes 4..7 ASCII `ftyp`; JPEG: erste Bytes FF D8 FF, letzte FF D9.
   Das ersetzt keine Decoder-/Codec-/Dauer-/Dimensionsprüfung beim späteren
   Medienimport. Nach Paketprüfung sichere lokale Blob-URLs erzeugen,
   beim Schließen widerrufen. Titel/Warnungen ausschließlich als Text rendern.

## JavaScript-Abbildung

Alle Zählwerte und Produkte dieser Version liegen unter `Number.MAX_SAFE_INTEGER`.
Little Endian ausdrücklich angeben; niemals Plattform-Endianness voraussetzen:

```js
const poseView = new DataView(poseBytes.buffer, poseBytes.byteOffset, poseBytes.byteLength);
const value = poseView.getFloat32((frame * 231 + joint * 7 + field) * 4, true);
const timeView = new DataView(timeBytes.buffer, timeBytes.byteOffset, timeBytes.byteLength);
const seconds = timeView.getFloat64(frame * 8, true);
// Number.isFinite, Number.isNaN, Number.isInteger für semantische Regeln.
const hash = await crypto.subtle.digest('SHA-256', payloadBytes);
const hex = Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
```

Web Crypto verarbeitet einen vollständigen Buffer; für große Pakete später
streamenden SHA-256 im Worker oder geringere Importlimits verwenden. Keine
ZIP-Bibliothek einsetzen, die unkontrolliert `unzip all` im UI-Thread ausführt.
Die ZIP-Bibliothek muss die Header-/CRC-/Overlap-Prüfung gewährleisten und
streamende Ausgabe begrenzen können. In dieser Phase gibt es bewusst keinen
Browser-Importer und keine zusätzliche produktive JS-Abhängigkeit.

Konformitätsdaten: `tests/fixtures/synthetic.choreo` sowie die Mutationen in
`tests/test_choreo.py` als verpflichtende positive und negative Testfälle für
spätere JavaScript-Implementierungen übernehmen.
