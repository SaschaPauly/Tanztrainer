# Android-Kameratest und Fehlerdiagnose

## Voraussetzungen

1. App über eine **HTTPS**-Adresse im aktuellen Chrome für Android öffnen (nicht in WhatsApp/anderen In-App-Browsern).
2. Chrome unter Android: App-Info → Berechtigungen → Kamera zulassen; in Chrome Website-Einstellungen → Kamera prüfen. Wortlaut je Android-Version unterschiedlich.
3. Browserseite neu laden, „Kamera testen (bevorzugt vorne)“ ausführen. „Kameradiagnose“ aufklappen und gegebenenfalls aktualisieren. Noch **kein** MediaPipe und **kein** Referenzvideo erforderlich.
4. Nach Freigabe Bild, Auflösung und Track-State anzeigen. Stoppen → Kamerakontrollleuchte sollte erlöschen.
5. Erst danach Pose-Modell laden, Referenzvideo importieren, Training starten. Separat Vollbild, Audio und Aufnahme prüfen.

## Diagnosetabelle

| Symptom | Vermutung | Nachweis / Abhilfe |
| --- | --- | --- |
| `isSecureContext=false` | `http://` auf LAN-IP oder ungeeignete Datei-Ansicht | HTTPS-Domain oder `localhost` auf **dem jeweiligen Gerät** |
| `mediaDevices` fehlt | unsicherer Kontext / Browser-Einschränkung | Chrome direkt öffnen, HTTPS prüfen |
| `NotAllowedError` | Berechtigung verweigert / Richtlinie / In-App-Browser | Android- und Website-Kamerarechte prüfen, Chrome direkt |
| `NotFoundError` | keine verfügbare Kamera | Kamera-/Gerätekonfiguration prüfen |
| `NotReadableError` | Kamera belegt oder Hardware-/Treiberproblem | andere Kamera-Apps schließen, neu versuchen |
| Livebild ok, Training scheitert | MediaPipe, Fullscreen, Audio, CaptureStream oder Performance | Komponenten einzeln testen; Fallback ohne Aufnahme/Vollbild |
| Kamera funktioniert, aber schwarze Vorschau | Video-Metadaten, Wiedergabe, Canvas, Hintergrundmaskierung | Roh-Video ohne Canvas/Segmentation anzeigen |
| Erkennung laden scheitert | CDN/Modellzugriff, Netzwerk, WASM | Fehlermeldung und Netzwerkkonsole, Modell separat testen |

## Testmatrix

- Android Chrome: HTTPS / HTTP-LAN / Datei-URL (letztere nur zur Fehlerreproduktion)
- Kamera erlaubt / verweigert / nachträglich aktiviert
- Vorder-/Rückkamera (falls vorhanden)
- Hoch-/Querformat, Display aus/an, Tabwechsel
- Ohne Modell / mit Modell; ohne Video / mit Video
- Aufnahme aktiviert/deaktiviert; WebM/MP4-Kompatibilität
- Vollbild unterstützt/nicht unterstützt
- Audio stumm/aktiviert; Tonspur vorhanden/fehlend
- Längere Trainingseinheit und Stop/Neustart

**Wichtig:** Eine Website kann Android-Kameraberechtigungen nicht selbst erzwingen. Bei blockierter Berechtigung muss der Nutzer diese in Android/Chrome ändern. Das Installieren als PWA umgeht diese Sicherheitsregel nicht.

## Zusätzliche Abnahmefälle für die Kamerasteuerung

- Keine Erkennung laden und kein Video auswählen: Schnelltest muss die unbearbeitete Livevorschau zeigen, ohne externe Downloads oder Aufnahme. Auch bei aktivierter Hintergrundmaskierung bleibt die Testvorschau unbearbeitet.
- Bei einer ungeeigneten bevorzugten Kamera „Ohne Kameravorgabe testen“ ausdrücklich wählen. Dieser Versuch verwendet jede verfügbare Kamera, nicht zwingend die Frontkamera. Gezielter Gerätewechsel ist noch nicht implementiert.
- Berechtigungsdialog offen lassen, dann Test stoppen bzw. Seite verlassen. Wird danach noch freigegeben, darf kein verspäteter Stream weiterlaufen. Anschließend bewussten Neustart prüfen.
- Bei verweigerter Berechtigung Android-App-Recht und Website-Recht getrennt prüfen. Eine Permissions-API-Abfrage kann fehlen oder unvollständig sein; sie entscheidet nicht über den Startversuch.
- Kamera durch andere App belegen bzw. Betriebssystem-Kamerasperre aktivieren; Fehlermeldung und Wiederaufnahme nach manuellem Neustart prüfen.
- Unterbrechung, Tabwechsel und Pagehide prüfen: Track muss beendet sein, kein automatischer Wiederanlauf. Bei fehlendem Livebild wird nach 10 Sekunden abgebrochen; ein offener Berechtigungsdialog wird nicht automatisch erneut gestellt.
- Browserkennung ist nur ein Hinweis: Chrome, Samsung Internet, Firefox, Edge und Messenger-WebView separat auf echten Geräten testen. User-Agent-Erkennung kann unvollständig sein.
- Nach positivem Kameratest die vollständige bestehende Testmatrix einschließlich Modell, Video, Training, Ton, Spiegelung, Freistellung, Splitaufnahme, Nachanalyse und Bildpaaren abarbeiten. Das aktuelle Kamerainkrement ändert keine Pose-/Trainingslogik und stellt keine vollständige Phase-1-Abnahme dar.

Ergebnisprotokoll: Datum, Gerätemodell, Android-Version, Browser/Version, HTTPS-Adresse, Android-/Website-Kamerarechte, Schritte, Diagnose und beobachtetes Ergebnis lokal dokumentieren. Keine Video-/Kamerabilder oder vollständige Browserkennung ohne Zustimmung veröffentlichen. Automatisierter aktueller Stand: `docs/TEST_RESULTS.md`.
