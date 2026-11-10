# Showtanztrainer – zentrale Projektdokumentation

**Stand:** 10. November 2026  
**Repository:** https://github.com/SaschaPauly/Tanztrainer  
**Anwendung:** https://saschapauly.github.io/Tanztrainer/  
**Zweck:** Gemeinsame, versionierte Wissensgrundlage für Projektentscheidungen, ChatGPT und Codex.

> Diese Datei fasst rekonstruierbare Projektgespräche und nachprüfbare Repository-Informationen zusammen. Sie ist kein vollständiger Export aller ChatGPT- oder Codex-Unterhaltungen. Aussagen über Gerätefunktion sind nur dann bestätigt, wenn ausdrücklich als getestet dokumentiert.

## 1. Produktziel

Browserbasierter KI-gestützter Showtanztrainer für Karnevals-/Showtanzproben. Ein lokal ausgewähltes Referenzvideo wird mit einer Kameraaufnahme des Übenden kombiniert. Die Anwendung unterstützt das Nachtrainieren, die Haltungsbewertung und eine nachträgliche Betrachtung. Die Ausgangsversion ist **Tanztrainer V12** (`original/Tanztrainer V 12.html`).

## 2. Verbindliche Bestandsfunktionen

Beim Weiterentwickeln erhalten: lokaler Videoimport; Auswahl rechte Bildhälfte oder ganzes Bild; Kamera und Spiegelung; Hintergrundmaskierung; Musik; Trainingsansicht; Splitbild; Aufnahmen; Nachanalyse; Bildpaare; heuristischer Score und Zeitversatz; dreisekündiger Countdown. Für Einzelheiten und Einschränkungen gelten `AGENTS.md`, `README.md` und die Implementierung.

## 3. Bisherige Projektentscheidungen und Verlauf

| Datum | Thema | Entscheidung / Ergebnis |
|---|---|---|
| 20.10.2026 | GitHub | Repository eingerichtet; V12 als funktionale Referenz und Grundlage für Codex. |
| Oktober 2026 | Android-Kamera | Eigenständiger Kamera-Schnelltest und lokale Diagnose, unabhängig von Referenzvideo und Pose-Modell. |
| 02.11.2026 | GitHub Pages | HTTPS-Veröffentlichung; PC und Smartphone konnten die Seite öffnen. |
| 02.11.2026 | Videoabbruch | Anfangs vermuteter Fehler nach Countdown war laut Nutzertest ein Bedienungsfehler; **keinen** separaten Reparaturauftrag dafür verfolgen. |
| 02.11.2026 | Vortänzer-Zoom | Statische automatische Voranalyse des gesamten Videos; Kopf und Füße sollen möglichst groß und vollständig erscheinen, mit Sicherheitsreserve; **keine dynamische Nachführung**. |
| 02.11.2026 | Pull Request #2 | `Statischer automatischer Videozoom mit lokaler Voranalyse` wurde in `main` gemergt (Merge-Commit `4fd50088c2fec1e22f74afc3411a2806044b7ee6`). |

PR: https://github.com/SaschaPauly/Tanztrainer/pull/2

## 4. Technischer Ist-Stand (nach Repository-Dokumentation)

- Statische Web-App mit `index.html`, `src/app.js`, `src/camera.js`, `src/zoom.js` und `src/styles.css`.
- MediaPipe PoseLandmarker; Modell und Bibliotheksdateien werden extern geladen. Keine vollständige Offline-Unterstützung behaupten.
- Automatischer Videozoom: lokale Pose-Voranalyse, konstant gehaltener Ausschnitt, standardmäßig aktiviert, abschaltbar, sicherer Fallback bei unzuverlässiger Analyse.
- Analysegrenzen: maximal fünf Minuten Video, 1.800 Stichproben und 90 Sekunden Gesamtzeit. Weitere Details, Grenzfälle und Geometrie in `docs/AUTOMATIC_VIDEO_ZOOM.md`.
- Kein eigener Upload-Endpunkt für Kamera- oder Referenzvideobilder. Keine Telemetrie oder externe Medienübertragung ohne ausdrückliche Zustimmung ergänzen.
- GitHub Pages auf `main`; Codeänderungen sind nicht automatisch als reale Android-Funktionstests zu werten.

## 5. Tests und offene Punkte

**Dokumentierte automatische Tests zu PR #2:** 19 Chromium-Browsertests und vier Node-Geometrietests bestanden. Diese nutzen simulierte Kamera und synthetische Posen/Clips, nicht die reale Tanzaufnahme.

**Offen / nicht nachgewiesen:**
1. Geräteabnahme auf Samsung Galaxy S24+ in Chrome Android mit echten Tanzvideos.
2. Prüfen, ob beim statischen Zoom schnelle Bewegungen, Drehungen, Arme, Kopf und Füße vollständig sichtbar bleiben.
3. Wiedergabeflüssigkeit, Analysezeit, Speicherbedarf, Musik-/Audio-Synchronität und Aufnahme mit aktivem Zoom prüfen.
4. Nach bestandenem Gerätetest entscheiden, ob die vorgesehene Version `v1.1.0` getaggt/veröffentlicht wird. Merge und GitHub-Pages-Bereitstellung sind **nicht** gleichbedeutend mit einem formalen Release.

Testpläne: `docs/ANDROID_TESTPLAN.md`, `docs/TEST_RESULTS.md`.

## 6. Vorgehen bei künftigen Änderungen

1. Vor Arbeitsbeginn diese Datei, `AGENTS.md`, `README.md` und einschlägige Dokumentation lesen.
2. Aktuellen Stand des `main`-Branches und offener Pull Requests prüfen; nicht allein auf alte Chat-Zusammenfassungen verlassen.
3. Anforderungen, Entscheidungen, Annahmen, Akzeptanzkriterien und offene Fragen trennen.
4. Kleine Änderungen auf einem eigenen Branch; Regressionstests und relevante Dokumentation aktualisieren.
5. Im Pull Request Tests, nicht getestete Gerätebedingungen, Datenschutzfolgen und bekannte Einschränkungen explizit nennen.
6. Bei abgeschlossener und freigegebener Änderung diese Datei mit Datum, PR-Link, Entscheidung und verbleibenden offenen Punkten fortschreiben.
7. Keine automatische Änderung am produktiven Code oder Merge allein aufgrund dieser Dokumentation.

## 7. Quellen und Rangfolge bei Widersprüchen

Für den **tatsächlich implementierten Stand** sind Code und Commit-Historie maßgeblich; für Testaussagen die reproduzierbaren Testberichte; für Anforderungen die jüngste ausdrückliche Nutzerentscheidung. Historische Chat-Zusammenfassungen sind Kontext, kein Ersatz für Tests.

- [Repository](https://github.com/SaschaPauly/Tanztrainer)
- [Pull Request #2](https://github.com/SaschaPauly/Tanztrainer/pull/2)
- [Automatischer Videozoom](AUTOMATIC_VIDEO_ZOOM.md)
- [Android-Testplan](ANDROID_TESTPLAN.md)
- [Testresultate](TEST_RESULTS.md)
- [Implementierungsplan](IMPLEMENTATION_PLAN.md)

## 8. Änderungsprotokoll dieser Wissensbasis

- **10.11.2026:** Erste konsolidierte Projektübersicht aus bekannten ChatGPT-Projektgesprächen und GitHub-Dokumentation angelegt. Die ursprünglichen Chat-/Codex-Transkripte wurden nicht importiert.
