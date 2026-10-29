# Technischer Umsetzungsplan – von Codex abzuarbeiten

## Phase 0 – Baseline sichern (P0)
- Aktuellen Stand in Git initialisieren; Originaldatei als unveränderte Referenz behalten.
- Syntaxprüfung und Smoke-Tests für UI und lokale Datei-URL durchführen. Statische Bereitstellung auf HTTPS einrichten (z. B. Vercel), ohne Zugangsdaten zu erfinden.
- Testprotokoll mit Browser, Android-Version, URL-Schema, Kamera-Berechtigung und reproduzierbarem Fehler anlegen.
- Prüfen, dass alle DOM-IDs und Handler nach Aufteilung unverändert funktionieren.
**Abnahme:** PC-Regression der V12-Kernfunktionen dokumentiert; HTTPS-URL für Android-Tests verfügbar oder konkrete Blockade genannt.

## Phase 1 – Android-Kamera stabilisieren (P0; vor allen anderen Features)
- Eigenständigen Kamera-Testbutton und Statusansicht implementieren: `isSecureContext`, `navigator.mediaDevices`, `getUserMedia`, `enumerateDevices` erst nach Berechtigung, `document.visibilityState`, unterstützte APIs, User-Agent/Browserinformation (nur lokal anzeigen), `video.readyState`, Auflösung, Track-Zustand.
- `getUserMedia`-Fehler nach `name` behandeln: `NotAllowedError`, `NotFoundError`, `NotReadableError`, `OverconstrainedError`, `SecurityError`, `AbortError`, `TypeError`; jeweils konkrete Handlungshinweise. Berechtigungsstatus nur abfragen, wenn API verfügbar; nicht allein darauf vertrauen.
- Android Chrome über HTTPS testen. Nicht voraussetzen, dass eine lokale `file://`-Datei oder LAN-HTTP zuverlässig Kamera freigibt. In-App-Browser als Sonderfall erklären.
- Kamerastart vom Pose-Modell und Referenzvideo entkoppeln. Falls `facingMode: user` scheitert, kontrollierten Fallback auf `{video:true,audio:false}` anbieten; Kamerawechsel nach Möglichkeit. `video.play()` und Video-Metadaten robust abwarten.
- Fehler bei `requestFullscreen`, `canvas.captureStream`, `MediaRecorder`, AudioContext isolieren und degradierten Trainingsmodus anbieten: Kamera + Referenz ohne Aufnahme/Vollbild muss funktionieren, wenn die APIs fehlen.
- CPU-/Speicherlast messen und `detect()` ggf. takten, Auflösung anpassen, Fehler abfangen; Test auf realem Android-Gerät zwingend für Abschluss.
**Abnahme:** Kamera-Schnelltest zeigt Livebild nach Berechtigung in Android Chrome auf HTTPS. Ablehnung/fehlende Kamera/HTTP/In-App-Browser führen zu verständlichen Meldungen. Stop schließt Kamera. Ohne MediaRecorder kann trainiert werden. Tests auf echtem Android-Gerät dokumentiert; andernfalls Phase als unbestätigt markieren.

## Phase 2 – Mobile UI & PWA (P1)
- Responsive Touch-Oberfläche; Querformat für Tanzvergleich; Orientierung nicht erzwingen, wenn Browser es nicht zulässt.
- PWA-Manifest, geeignete Icons (selbst erstellt), optional Service Worker mit versioniertem Cache für eigene statische Dateien. Modell-/CDN-Offlinefähigkeit separat testen; kein falsches Offline-Versprechen.
- Installationshinweis für Android Chrome, HTTPS, Kamera-Berechtigungen; Datenschutzseite.
**Abnahme:** App ist auf unterstütztem Android Chrome installierbar; Kamera funktioniert auf installierter PWA nach erneuter Freigabe; Offline-Grenzen sind korrekt beschrieben.

## Phase 3 – Rechte Tänzerin zuverlässig verfolgen (P1)
- Referenz-Video-Voranalyse mit `numPoses:2` oder geeignetem Multi-Personen-Modell und manueller Auswahl der Zielperson per Tippen auf Video. Zielperson über Frames verfolgen, auch bei Seitenwechseln; Identitätswechsel und Überlappungen erkennen und markieren.
- Keine unberechtigte Zusicherung perfekter Identitätsverfolgung. Bei unklarer Zuordnung anhalten oder Nutzer bestätigen lassen; manuellen Crop-Fallback erhalten.
- Auf Mobilgeräten Ressourcenlimit, Vorverarbeitung und Cache von Pose-Zeitreihen berücksichtigen.
**Abnahme:** Testclips mit zwei Personen, Seitenwechsel und zeitweiser Überdeckung; Zuordnung und Warnungen dokumentiert. Keine stille Auswahl der falschen Person.

## Phase 4 – Synchronisierung und Bewertung (P1)
- Kamerazeitstempel (monotone Uhr), Videozeit und Pose-Verarbeitungslatenz getrennt erfassen; kalibrierbaren Zeitoffset anbieten.
- Referenz-Pose-Zeitreihe vorab extrahieren; Live-Vergleich mit interpolierten Zeitpunkten. Robuste Erkennungsquote/Confidence und Missing-Data-Behandlung.
- Gelenkwinkel, relative Körperpositionen und zeitliche Bewegung ergänzen; Spiegelung korrekt behandeln. Bewertung nach Körperregion und Zeitabschnitt, nachvollziehbares Feedback.
- **Beat-Analyse** als separates optionales Modul (Audio-Onset/Tempo) mit klarer Unsicherheit, nicht mit Pose-Synchronität verwechseln. Musikrechte beachten.
**Abnahme:** Synthetische Zeitverschiebung und definierte Bewegungssequenzen testen; gemessene vs. bekannte Offsets mit Fehlertoleranzen dokumentieren. Keine irreführenden 0–100-Werte bei unzureichender Erkennung.

## Phase 5 – Animierte Referenztänzerin (P2)
- Referenz-Pose-Zeitreihe auf eine stilisierte, eigenständige Cartoon-Figur riggen (2D/3D nach Machbarkeitsprüfung); nicht behaupten, dass simples Video-Stylizing automatisch framegenaue Bewegungen erhält.
- Bewegungsübertragung mit Smoothing, Fußkontakt/Okklusion und plausibler Gelenkkinematik; Original-Audio auf derselben Timeline halten.
- Fallback Originalvideo, Animation optional abschaltbar. Kein fremdes Video an einen Cloud-Dienst übertragen ohne explizite Freigabe.
**Abnahme:** Export/Playback bleibt über volle Clipdauer innerhalb dokumentierter A/V-Toleranz; visuell erkennbare Tanzbewegungen, keine verdeckten Datenschutzänderungen.

## Phase 6 – Tests, Deployment, Dokumentation (laufend)
- Automatisierte Unit-/Integrationstests, Browser-Tests (Chromium Desktop, soweit möglich) und **manuelle** Android-Chrome-Tests.
- Vercel-Konfiguration, HTTPS, Cache-Versionierung, Build-/Deploy-Anleitung, Changelog und Fehlerdiagnose bereitstellen.
- Datenschutz: keine Uploads, keine ungefragte Telemetrie; externe Modellressourcen und Drittanbieterzugriffe offenlegen.

## Reihenfolge für Codex

**Jetzt implementieren: Phase 0 und Phase 1.** Anschließend Phase 2. Phasen 3–5 erst nach dokumentiert funktionierendem Android-Kamerazugriff und bestätigter Baseline. Bei blockierter Hardware-/Browserprüfung konkrete manuelle Prüfschritte liefern statt Tests zu erfinden.
