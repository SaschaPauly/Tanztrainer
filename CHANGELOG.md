# Änderungsprotokoll

## Showtanztrainer 2.0 – Phase 3: Windows-Oberfläche – 2026-11-22 (PR zur Prüfung)
- Native PySide6-Oberfläche und Doppelklickstarter: lokaler Videoimport, Lite-Download auf ausdrücklichen Aufruf, CPU/30-%-Standard, optionale Startperson-Markierung, Analyse im Hintergrund und kooperativer Abbruch.
- Validierte vorhandene Pakete ohne Neuanalyse öffnen; native Videovorschau mit farbigen Haltungspunkten, festem Zoom, exakten Einzelbildschritten und Qualitätsbericht. CSV-/SQLite-Ausgabe integriert.
- Normalisiertes Importvideo ohne erneute Kodierung wiederverwenden; Posen/PTS für die Vorschau speicherschonend einblenden. Paket erst nach Sichtprüfung ausdrücklich speichern, bestehende Ausgaben atomar schützen und temporäre Ressourcen freigeben.
- GUI-/Abbruch-/Auswahltests, Windows-CI und Bedienungsanleitung ergänzt. Webanwendung und .choreo-Schema unverändert; kein automatischer Merge.

## Zoomtoleranz 30 % und gezielte Zeitregel – 2026-11-22 (PR zur Prüfung)
- Standard für Analyse und Modellvergleich von 10 auf einschließlich 30 % unsichere Bilder erhöhen. Längere lokale Gelenkunsicherheit bei zuverlässigem Rumpf zulassen; Kern-/Zuordnungsverlust weiterhin ab über 0,5 s zum Ganzbild-Fallback führen lassen.
- Schulter-/Hüftbasis anhand tatsächlicher gespeicherter Punkte prüfen, getrennte Zeitspannen dokumentieren. Zuverlässige Extrema und Randreserve erhalten; keine Änderung an Haltungspunkten, Erkennungsgrenzen oder Bewertung.
- Zoom vorhandener Pakete ohne neue Modellerkennung berechnen; volle Frameabdeckung prüfen, Originaldaten und Audiooffset erhalten. Vorschau kann mit aktivem Lite-Zoom starten.
- Zwölf neue Regressionstests, Windows-CI und Dokumentation ergänzt. Schema und veröffentlichte Webanwendung unverändert; kein automatischer Merge.
## Skelettvorschau und Modellvergleich – 2026-11-22 (PR zur Prüfung)
- Lite, Full und Heavy auf identischen Zeitpunkten lokal vergleichen; synchronisierte Offline-Skelettvorschau mit farbigen Konfidenzen, Einzelbildschritten, Zusatzdetektionen und Zoomdarstellung.
- Expliziter Einpersonenmodus wählt eine deutliche Vordergrundfigur und prüft zeitliche Kontinuität. Mehrdeutige Kandidaten/Positionssprünge bleiben fehlend; Zusatzdetektionen werden nicht als nachgewiesene zweite Person gewertet.
- Getrennte Diagnose für alle 33 Punkte und acht Arm-/Beinabschnitte, Auswahlprotokoll, Modellidentität, Laufzeit und drei schemaidentische Pakete. Offizielle Modelle nur ausdrücklich herunterladen.
- Dreizehn neue Python- und vier Node-Tests, Windows-CI erweitert, lokale Chrome-Vorschau mit echtem Video geprüft. Webanwendung, Schema und Originalvideo unverändert; kein automatischer Merge.

## Zoomtoleranz – 2026-11-22 (PR zur Prüfung)
- Bis einschließlich 10 % unsichere Analysebilder für festen Zoom akzeptieren; CLI-Option `--zoom-max-uncertain-percent`, Prozentanteil und Grenze im Qualitätsbericht.
- Zuverlässige Extrema auch aus unsicheren Bildern erhalten, zusätzliche 5 % Randreserve. Bei längeren Erkennungslücken, Zeitlücken, Bildrandnähe oder Sampling weiterhin Ganzbild-Fallback. Binärdaten, Format und Webanwendung unverändert.
- Sieben neue Regressionstests für Grenzwert, Überschreitung, zusammenhängende Lücken, Mehrfachzählung, Randfälle und unveränderte Posewerte bei gültigem Export.

## Separate Haltungspunkt-Testausgabe – 2026-11-22 (PR zur Prüfung)
- Validierte `.choreo`-Daten ohne erneute Analyse separat als CSV und SQLite ausgeben, einschließlich exakter Zeitstempel, 2D-/geschätzter 3D-Werte, Konfidenzen und Missing-Kennzeichen.
- Bildtabelle, Zoom-/Qualitätsbericht und Leseanleitung ergänzen die Diagnose. Keine Änderung an Zoomalgorithmus, Quellvideo, Paketformat oder Webanwendung.
- Fünf Regressionstests für Zahlen-/Zeitstempeltreue, Missing-Daten, Quellschutz, ungültige Pakete und Abbruch; Windows-CI erweitert.

## Analyzer-Importkorrektur – 2026-11-22 (PR zur Prüfung)
- Fehlende Pixelverhältnis-Metadaten (`0/1`) beim Import akzeptieren und als quadratische Pixel ausgeben; Regressionstest für unveränderte Abmessungen und PTS. Originalvideo, Schema und Webanwendung bleiben unverändert.
- Original-Zeitbasis beim Neukodieren übernehmen, damit auch Zeitstempel zwischen nominalen FPS-Rasterpunkten erhalten bleiben; Regression mit 5-ms-Versatz ergänzt.

## Showtanztrainer 2.0 – Phase 2: CLI-Analyzer – 2026-11-22 (PR zur Prüfung)
- Lokaler Windows-Python-Analyzer mit MediaPipe Tasks (33 Punkte, 2D und hüftrelatives geschätztes 3D), GPU-Prüfung und CPU-Fallback.
- H.264/AAC-Import mit physischer Orientierung, VFR-PTS, frameweiser Verarbeitung und Ressourcenlimits.
- Konservativer fester Ganzkörperzoom, Qualitätswarnungen mit Zeitbezug, schemaidentischer `.choreo`-Export mit Hashes und vollständiger Validierung vor atomarem Speichern.
- Reproduzierbare Medientests und Windows-CI, Installations-/CLI-Dokumentation; Windows-Pfadtest des vorhandenen Validators korrigiert.
- Keine Änderung an `index.html`, `src/`, `original/`, Schema, Pages-Konfiguration oder Browserverhalten. Kein automatischer Merge. GUI, Browserimport und Personentracking folgen separat.

## v1.1.0 vorgesehen – Automatischer Videozoom – 2026-11-02
- Lokale Voranalyse des vollständigen gewählten Referenzbereichs mit vorhandenem MediaPipe-Modell, zeitlicher und adaptiver Abtastung, Konfidenz-/Plausibilitätsprüfungen und Sicherheitsreserven.
- Konstanter, fensterabhängiger Ausschnitt für Trainingsansicht und Splitbild-Aufnahme; keine dynamische Nachführung. Haltungsbewertung und ursprünglicher Analysebereich bleiben erhalten.
- Standardmäßig aktivierter Schalter, lokal gespeicherte Wahl, inhaltsbasierter Cache, Statusanzeige und manueller Fallback. Countdown startet erst nach abgeschlossenem Ergebnis oder sicherem Fallback.
- Ressourcenlimits, Abbruch und Decoderfreigabe; Kameravorschau bleibt verfügbar, parallele Hintergrundmasken-Inferenz wird vermieden.
- Keine neuen Laufzeitabhängigkeiten, Uploads, Releases, Tags, Merges oder Veröffentlichungen. Automatisierte Testdetails und offene Android-Geräteabnahme siehe docs/TEST_RESULTS.md.


## Kameradiagnose – 2026-10-29
- Unabhängiger Rohkamera-Test ohne Referenzvideo oder Pose-Modell; expliziter Fallback ohne Kamera-/Auflösungsvorgabe.
- Lokale Diagnose für sicheren Kontext, Browserhinweise, Kamera-APIs, Berechtigung, Geräteanzahl nach Freigabe, Auflösung und Track-Zustand.
- Konkrete Hinweise für Berechtigungs-, HTTPS-, Geräte-, Sicherheits- und Wiedergabefehler; keine automatischen Neuversuche.
- Stop, Tabwechsel und Pagehide entwerten ausstehende Anfragen; verspätete Streams werden geschlossen. Beendete Tracks werden behandelt.
- 13 automatisierte Chromium-Tests bestanden; echter Android-Test und vollständige V12-Geräteabnahme stehen aus. Details in docs/TEST_RESULTS.md.
- Pose-Erkennung, Bewertung, Timing, Aufnahme- und Trainingslogik unverändert; bestehende Kamera-/Stop-Schaltflächen nutzen die neue Kamerasteuerung.

## Codex-Übergabe – 2026-10-20
- V12-Code ohne Funktionsänderung in HTML/CSS/JS getrennt.
- Codex-Arbeitsauftrag, Android-Diagnoseplan und Roadmap ergänzt.
- Keine Android-Fehlerbehebung durchgeführt oder behauptet.

## Unveröffentlicht – Showtanztrainer 2.0, Phase 1 (2026-11-16)

- Separater Formatvertrag `showtanz-choreo` 1.0.0 mit JSON-Schema,
  MediaPipe-Gelenkreihenfolge, binären Posen/Zeitstempeln und festem Zoom.
- Offline-Python-Validator mit Größen-, ZIP-Sicherheits-, Hash- und
  Semantikprüfung; sprachunabhängiger Vertrag für spätere JavaScript-Importer.
- Eigene synthetische CC0-Testmedien als .choreo-Paket, Generator und
  automatisierte Positiv-/Negativtests.
- Bestandsaufnahme, bestätigte GitHub-Pages-Konfiguration und Integrationsplan.
- Produktive Webdateien unverändert; kein Merge, Deployment oder neue Livefunktion.
