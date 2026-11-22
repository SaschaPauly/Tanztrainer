# Offline-PC-Analyzer: Architekturgrundlage

Dieser Ordner enthält zunächst nur Dateiformatwerkzeuge. Noch keine
Videoanalyse, GUI, Live-Erkennung oder Bewertung. Der Validator ist unabhängig
von Browser/Windows-GUI und funktioniert mit Python 3.11+ unter Windows/Linux.

Windows PowerShell, ab Repositorywurzel:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r analyzer/requirements.txt
.\.venv\Scripts\python -m analyzer.validate tests/fixtures/synthetic.choreo
.\.venv\Scripts\python -m unittest discover -s tests -p test_choreo.py -v
```

Linux/macOS: `python3 -m venv .venv`, dann `.venv/bin/python -m pip install -r
analyzer/requirements.txt`; die gleichen Modulbefehle mit `.venv/bin/python`.
Validator: Exitcode 0 bei gültigem Paket, 1 mit deutscher Fehlermeldung bei
ungültigem Paket. Kein Extrahieren und keine Netzwerkanfragen bei Validierung.
Die Installation lädt die deklarierte jsonschema-Abhängigkeit und deren
Abhängigkeiten aus dem konfigurierten Paketindex.

Das eingecheckte Beispiel braucht zum Prüfen kein FFmpeg. Zum Neuerzeugen:
FFmpeg mit libx264 installieren und `python -m analyzer.create_example`
ausführen. Erzeugt 1 s blaues Video, vier anatomisch geordnete synthetische
Posen und ein selbst erzeugtes Vorschaubild. Keine Modellerkennung simulieren:
die Quelle heißt ausdrücklich `synthetic-fixture`. Alle generierten Testmedien
und synthetischen Daten werden unter CC0-1.0 bereitgestellt (siehe Fixtures).
Gleiche FFmpeg-Version ergibt reproduzierbare Medien; Byteidentität über
verschiedene Encoder-Versionen wird nicht versprochen. ZIP-Zeit und Reihenfolge
sind fest, alle Größen/Hashes werden aus den erzeugten Bytes berechnet.

Alle vorhandenen Browserregressionen zusätzlich nach README ausführen:
`python -m pip install -r tests/requirements.txt`,
`CHROMIUM_PATH=/usr/bin/chromium python -m unittest discover -s tests -v`,
`node tests/zoom.test.cjs` und `node --check` für alle drei `src/*.js`.
Windows: Umgebungsvariable/Chromium-Pfad entsprechend anpassen. Echte
Android-/Windows-Geräteprüfungen sind getrennte manuelle Abnahmen.
