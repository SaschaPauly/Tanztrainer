# Änderungsprotokoll

## Analyzer-Importkorrektur – 2026-11-22 (PR zur Prüfung)
- Fehlende Pixelverhältnis-Metadaten (`0/1`) beim Import akzeptieren und als quadratische Pixel ausgeben; Regressionstest für unveränderte Abmessungen und PTS. Originalvideo, Schema und Webanwendung bleiben unverändert.

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
