# Kameradiagnose: Analyse und Teststatus

Stand: 2026-10-29. Dieses Inkrement betrifft den Kamerazugriff; Phase 1 ist noch nicht vollständig abgenommen.

## Ausgangslage und Änderung

Der V12-Kamerastart prüfte bereits isSecureContext und getUserMedia, zeigte aber nur eine generische Fehlermeldung. Das Livevideo war versteckt; die sichtbare Vorschau hing von canvas.captureStream ab. Es gab keinen expliziten Fallback ohne bevorzugte Kamera, keine Diagnose und keine Entwertung ausstehender Berechtigungsanfragen. Stop während eines offenen Dialogs konnte deshalb von einem verspätet erfolgreichen Start überholt werden.

src/camera.js kapselt nun Anfrage, unbearbeitete Vorschau, Wiedergabe-/Bildbereitschaft (10 Sekunden Timeout nach Freigabe), Fehlerhinweise und Abbruch. Die bisherigen Kamera- und Stop-Schaltflächen sind angebunden. Eine fehlende Permissions-API blockiert den Test nicht. enumerateDevices wird erst nach erfolgreicher Freigabe verwendet; angezeigt wird nur die Anzahl der Kameras. Die Browserkennung und Diagnose verbleiben lokal, ohne Speicherung, Telemetrie oder Upload.

PoseLandmarker, detect, Trainingsstart, Scoring, Timing, Audio und Aufnahmeverfahren wurden nicht verändert. Der zentrale Stop-Pfad gibt zusätzlich die Kamerasteuerung frei. Das Original in original/ blieb unverändert.

Weitere bekannte Grenzen der V12 bleiben bestehen: synchrones IMAGE-Inferencing, browserabhängige MediaRecorder-/captureStream-Unterstützung, Canvas-Vollbildvorschau und Audiofreigabe nach Nutzeraktion. Der unabhängige Kameratest läuft ohne diese optionalen APIs; daraus folgt keine Zusage, dass der bestehende Trainingsablauf ohne sie vollständig funktioniert. Dieses Inkrement verändert diese Trainingslogik ausdrücklich nicht.

## Automatisierte Ausführung

Umgebung: Linux, Python 3.12.14, Playwright 1.62.0, Chromium 154.0.8037.57, Node.js 24.19.0. Kein Android-Gerät verfügbar.

```sh
python3 -m unittest discover -s tests -v
node --check src/camera.js
node --check src/app.js
git diff --check
```

Browserlauf: **13 Tests bestanden**, 0 Fehler, 0 fehlgeschlagen, 0 übersprungen. JavaScript-Syntax und Diff-Whitespace geprüft.

| Test | Nachgewiesenes Verhalten |
| --- | --- |
| independent_camera_and_restart | Test ohne Modell/Video, Bild 640×480, kein Mikrofon, keine externen Requests, Stop und Neustart über bestehende Schaltflächen |
| named_errors_and_explicit_fallback | Acht simulierte Fehlernamen mit passenden Hinweisen; genau ein Anfrageversuch, anschließend ausdrücklich gewählter Fallback mit video:true/audio:false |
| insecure_http_origin | Echter unsicherer HTTP-Testursprung wird vor einer Kameraanfrage mit HTTPS-Hinweis abgewiesen |
| missing_camera_api | Fehlende mediaDevices-API wird erklärt |
| android_browser_hints | Vier simulierte Browserkennungen zeigen Hinweise für WebView, Samsung Internet, Firefox und Edge; kein Kompatibilitätsnachweis |
| no_optional_apis_or_permissions_query | Rohkamera funktioniert ohne Permissions-Abfrage, captureStream, MediaRecorder, AudioContext und Fullscreen |
| no_device_enumeration_before_grant | Keine Geräteabfrage vor erfolgreicher Kamerafreigabe |
| stop_cancels_pending_permission_and_stale_stream | Stop entwertet ausstehende Anfrage; verspäteter alter Stream endet, ein neuer Versuch bleibt unbeeinträchtigt |
| stop_while_video_play_pending | Stop beendet Kamera auch bei nicht abgeschlossener Video-Wiedergabe |
| pagehide_visibility_and_track_ended | Tracks und Videoquellen werden bei Pagehide, verborgenem Dokument und Track-Ende freigegeben |
| video_failure_releases_camera | Wiedergabefehler beendet alle erworbenen Kameratracks |
| video_timeout_releases_camera | Nach 10 Sekunden ohne abspielbares Video endet der Stream; Uhr im Test gezielt vorgespult |
| v12_import_effects_training_recording_smoke | Synthetischer lokaler WebM-Import, Crop-Wechsel, Spiegelungs-/Hintergrund-Steuerelemente, Trainingsstart, beide Aufnahme-Downloads und Wiedergabetempo |

Die Tests verwenden echte Chromium-Medien-APIs mit simulierter Kamera. Berechtigungsfehler, Browserkennungen und fehlende APIs werden injiziert. Der V12-Smoke-Test ersetzt ausschließlich das externe Pose-Modul durch einen Testersatz ohne erkannte Posen; er prüft Ablauf und Aufnahme, keine Erkennungsqualität. Kein externer Modell-Download ist für die Suite erforderlich.

## Noch nicht geprüft

- Echtes Android Chrome über öffentliches HTTPS, reale Berechtigungsdialoge, Front-/Rückkamera und belegte Hardware.
- Samsung Internet, Firefox, Edge und Messenger-Browser auf echten Geräten.
- Reale Modell-/WASM-Inferenz, Pose-/Timingqualität, Audio-Synchronität und Langzeitperformance.
- Vollständige V12-Regression mit echtem Tanzvideo einschließlich Nachanalyse und Bildpaaren sowie Geräte-Fallbacks für optionale Trainings-APIs.

Es wurde kein öffentliches HTTPS-Deployment angelegt. Vercel-Anleitung in README.md, manuelle Schritte in docs/ANDROID_TESTPLAN.md. Geräteabnahme und vollständiger Phase-1-Abschluss dürfen erst nach diesen Tests behauptet werden.
