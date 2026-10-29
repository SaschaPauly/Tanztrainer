# Änderungsprotokoll

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
