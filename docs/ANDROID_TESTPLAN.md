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


## Statischer Autozoom (v1.1.0 vorgesehen, Geräteabnahme offen)

1. GitHub-Pages-HTTPS bzw. PR-Preview direkt in Android Chrome auf dem Galaxy S24+ öffnen. Modell laden, lokale Clips im Hoch- und Querformat mit unterschiedlichen Auflösungen, Abständen und Perspektiven importieren. Auch „rechte Bildhälfte“ und „ganzes Bild“ prüfen.
2. Auf Status warten; Start muss während der Analyse gesperrt sein. Kamera schon währenddessen starten: Vorschau muss weiterlaufen. Analysezeit, groben Spitzenspeicher und Reaktionsfähigkeit dokumentieren. Hintergrundfarbe bei aktiver Voranalyse separat prüfen (Maskeninferenz pausiert).
3. Ganzes Video mit seitlichen Bewegungen, großen Armen, Ausfallschritten und Drehungen abspielen. Kopf, Hände, Füße und Sicherheitsrand prüfen; zwischen Start und Ende darf der Bildausschnitt nicht wandern. Bildschirm drehen, Musik und Splitbildaufnahme prüfen. Kamera wie zuvor spiegeln und Hintergrundeffekte testen.
4. Clips ohne Person, mit verdeckten Füßen, mehreren Personen und ungeeignetem Format prüfen: konservativer Fallback, kein unsicherer Zusatzzoom. Bei mehreren Personen ist manuelle Ausschnittwahl erforderlich; keine Identitätsgarantie.
5. Analyse überspringen, währenddessen Stop/Tabwechsel ausführen und Datei/Ausschnitt wechseln: kein verspätetes Überschreiben, keine weiterlaufenden Decoder. Nach sicherem Fallback muss der normale Start möglich sein.
6. Dasselbe unveränderte Video erneut importieren und Seite neu laden: Cachemeldung, keine neue Poseanalyse. Dateiinhalte ändern: neue Analyse. Browserdaten löschen: Cache entfernt. Privater Modus/gesperrter Speicher: keine Funktionsblockade.
7. Autozoom aus/ein, Wahl nach Reload, gespeicherte Splitbilddatei, Nachanalyse, Bildpaare, Score und Zeitversatzanzeige gegen Baseline vergleichen. Autozoom aus muss die vorherige Darstellung zeigen. Nach Stop Kamera-LED/Tracks prüfen.
8. Clip >5 Minuten oder Ressourcen-/Timeoutfall: bisherige Darstellung des vollständigen Videos; kein Zoom aus einer unvollständigen Anfangsanalyse.

Pro Fall Browser-/Android-Version, Clipdauer/-format, Ausschnittwahl, Analysezeit, Erkennungsprobleme und Ergebnis protokollieren. Diese Liste ist keine bereits erfolgte Geräteprüfung.
