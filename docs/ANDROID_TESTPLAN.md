# Android-Kameratest und Fehlerdiagnose

## Voraussetzungen

1. App über eine **HTTPS**-Adresse im aktuellen Chrome für Android öffnen (nicht in WhatsApp/anderen In-App-Browsern).
2. Chrome unter Android: App-Info → Berechtigungen → Kamera zulassen; in Chrome Website-Einstellungen → Kamera prüfen. Wortlaut je Android-Version unterschiedlich.
3. Browserseite neu laden, Kamera-Schnelltest ausführen. Noch **kein** MediaPipe und **kein** Referenzvideo erforderlich.
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
