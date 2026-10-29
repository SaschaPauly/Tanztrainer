# Codex: verbindlicher Projektauftrag

Du entwickelst den Karnevals-Showtanztrainer auf Grundlage von Version 12 weiter. Die HTML-Datei in `original/` ist die funktionale Referenz. `index.html` und `src/` sind der bearbeitbare Stand. **Ziel: zuerst verlässlich auf Android starten, danach Tracking, Timing und optional Animation verbessern.**

## Arbeitsregeln

1. **Phase 0 und 1 zuerst** (siehe `docs/IMPLEMENTATION_PLAN.md`), dann weitere Phasen in Reihenfolge. Liefere kleine, überprüfbare Änderungen und dokumentiere jeweils Tests und offene Risiken. Wenn keine Android-Testumgebung verfügbar ist, ausdrücklich angeben; keine Gerätekontrolle behaupten.
2. Bestehende Features erhalten: lokaler Videoimport, Auswahl rechte Bildhälfte/ganzer Frame, Kamera, Spiegelung, Hintergrundmaskierung, Musik, Training, Splitbild, Aufnahmen, Nachanalyse, Bildpaare, Score, Zeitversatzanzeige. Bei nötigen Änderungen Regressionstests ergänzen.
3. **Datenschutz:** Kamera und Referenzvideo lokal verarbeiten. Keine externen Video-/Frame-/Pose-Uploads, Analytics, Nutzerkonten oder Tracking ohne explizite Zustimmung. Drittanbieter-Downloads transparent machen. Keine Geheimnisse einchecken.
4. Fehlermeldungen müssen zwischen unsicherem Ursprung, fehlender Geräte-API, verweigerter Berechtigung, fehlender Kamera, blockierter/anderweitig belegter Kamera, Modell-Ladefehler und Browserinkompatibilität unterscheiden. Keine automatische Endlosschleife für Berechtigungsdialoge.
5. Mobile zuerst: Chrome Android, Hoch-/Querformat, Touch, `playsinline`, Performance-/Speichergrenzen, Aussetzen bei Hintergrundwechsel, Audiofreigabe nach Nutzerinteraktion. Kamera bei Stop und Pagehide zuverlässig schließen.
6. Abweichungsbewertungen als **heuristisch** kennzeichnen; keine wissenschaftlich validierte Präzision oder automatische Takterkennung vortäuschen.
7. Änderungen am Tracking/Timing nur mit reproduzierbaren Tests; Performance-Profiling und Fallback bei fehlender GPU/WASM. Kein Abbruch des gesamten Trainings, wenn eine optionale Funktion nicht unterstützt wird.
8. PWA nur mit sauberer HTTPS-Bereitstellung, installierbarem Manifest und bewusstem Cache-Konzept. Externe MediaPipe-Dateien nicht stillschweigend als offline verfügbar bezeichnen. Keine Kameraberechtigung durch PWA-Installation versprechen.
9. Nach jeder Phase README, Changelog und Teststatus aktualisieren; klare Anweisungen für Vercel-Deployment bereitstellen. Frage nach erforderlichen Zugangsdaten statt sie zu erfinden.

## Erster Arbeitsschritt

Analysiere `src/app.js` auf Android-spezifische Risiken (u.a. `window.isSecureContext`, `getUserMedia`, Fullscreen, `captureStream`, `MediaRecorder`, MediaPipe `detect`, AudioContext). Implementiere zunächst eine Kamera-Diagnoseansicht und einen eigenständigen Kamera-Schnelltest, der **ohne Referenzvideo und ohne geladenes Pose-Modell** funktioniert. Danach erst weitere Verbesserungen.
