# Automatischer statischer Videozoom (v1.1.0 vorgesehen)

## Bedienung

„Automatischer Zoom: Ein / Aus“ ist standardmäßig eingeschaltet; die Wahl bleibt nach Möglichkeit lokal gespeichert. Eigenes Video importieren und wie bisher „Erkennung laden“ wählen. Sobald beides vorhanden ist, beginnt die Voranalyse. Die Starttaste ist bis zum Ergebnis gesperrt; der bestehende dreisekündige Countdown bleibt unverändert. „Ohne zusätzlichen Zoom fortfahren“ wählt sofort den sicheren Fallback. Auch bei Fehlern oder nach spätestens 90 Sekunden wird die bisherige Darstellung freigegeben. Ein geladenes Pose-Modell bleibt wie bisher Voraussetzung für den Haltungsvergleich.

Der Ausschnitt gilt jeweils für die manuell gewählte rechte Bildhälfte oder das ganze Bild. „Ganzes Bild“ ist für eine einzelne Person vorgesehen. Das bestehende Ein-Personen-Modell kann bei mehreren Personen die Identität wechseln; es gibt keine verlässliche Identitätsverfolgung. Prüfen, dass die gewünschte Person vollständig im gewählten Ausgangsausschnitt bleibt. Während Training, Countdown, Aufnahmefertigstellung und Nachanalyse sind Dateiauswahl, Ausschnitt und Zoomschalter gesperrt.

Die große Trainingsansicht, ihre Vorschau und die Splitbild-Aufnahme verwenden denselben Bewegungsrahmen. Wegen unterschiedlicher Fensterverhältnisse können sich Zoomfaktoren zwischen diesen Ansichten unterscheiden; innerhalb jeder Ansicht bleiben sie über das gesamte Training konstant. Der bereits vorhandene 16:9-Trainingscanvas bleibt auch bei Bildschirmdrehung unverändert. Originaldatei, Haltungsbewertung, Nachanalyse, Bildpaare, Kamera, Android-Videoplayer und Musikpfad verwenden weiterhin ihre bisherigen Daten bzw. Verfahren. „Verwendeten Referenzausschnitt prüfen“ zeigt weiterhin den ursprünglichen Analysebereich für die Bewertung.

## Analyse und Sicherheit

`src/zoom.js` verwendet das bereits geladene MediaPipe PoseLandmarker Lite 0.10.21 im IMAGE-Modus über `detectLandmarks`. Es lädt weder ein zweites Modell noch neue Laufzeitbibliotheken. Ein separater stummer `playsinline`-Videodecoder springt zu Stichproben; das eigentliche Wiedergabevideo wird nicht gesucht oder abgespielt. Inferenzcanvas: längste Kante maximal 384 Pixel, ursprüngliches Seitenverhältnis. Keine Frame-/Pose-Zeitreihe wird gespeichert. MediaPipe-Ergebnisse und Segmentierungsmasken werden durch den bestehenden Adapter geschlossen.

Abtastung vom Anfang bis unmittelbar vor das Ende, maximal 0,5 Sekunden Abstand. Bewegen sich die Grenzen auf einer Achse zwischen zwei Stichproben um mehr als 3,5 % der Bilddimension, kommen Zwischenproben mit 0,125 Sekunden Abstand hinzu. Nach jedem Bild wird an die Ereignisschleife abgegeben. Maximal 300 Sekunden Videodauer, 1800 Stichproben, 8 Sekunden je Medienereignis und 90 Sekunden Gesamtbudget einschließlich Dateifingerabdruck; Überschreitung ergibt Fallback für das gesamte Video, niemals einen Ausschnitt nur aus dem Videoanfang.

Nase, Ohren und sämtliche 22 Körperpunkte von Schulter bis Fußspitze müssen in jeder untersuchten Pose vorhanden sein. Visibility und gegebenenfalls Presence mindestens 0,65; Koordinaten endlich und innerhalb des Ausgangsbilds. Sehr kleine/degenerierte Körperrahmen und unplausible Torsolängen werden verworfen. Fehlende Erkennung oder offensichtliche Ausreißer führen zu keinem zusätzlichen Zoom. Unsichere Frames werden nicht einfach aus der Vereinigung gelöscht. Plausible große Ausdehnungen bleiben erhalten, auch wenn sie nur einmal auftreten; es gibt keine Quantilfilter, die echte Armbewegungen wegschneiden könnten.

Alle gültigen Rahmen werden vereinigt. Dazu kommen **5 % der jeweiligen Bilddimension je Seite** sowie oberhalb weitere 8 % der erkannten Körperhöhe, da Gesichtspunkte den Scheitel nicht abbilden. Reserven enden an den Grenzen des ausgewählten Ausgangsbilds. Schon im Original abgeschnittene Körperteile können nicht wiederhergestellt werden.

**Stichproben und Pose-Schätzung garantieren keine vollständige Sichtbarkeit in jedem ungemessenen Zwischenbild.** Besonders schnelle Bewegungen, Verdeckungen, Kostüme und mehrere Personen bleiben Grenzen. Konservative Reserven und Fallback reduzieren das Risiko. Bei solchen Clips Zoom ausschalten oder ganzes Bild verwenden. Es gibt weder dynamische Nachführung noch Kameraschwenks während der Wiedergabe.

## Geometrie

Die gespeicherte Box `(x,y,w,h)` ist auf den gewählten Ausgangsausschnitt normiert. Für Quellgröße `(sw,sh)` wird sie in Pixel umgerechnet. Die Box wird zentriert bis zum Seitenverhältnis des Zielfensters erweitert, soweit das Original Platz bietet; ihre Lage wird innerhalb der Quelle begrenzt. Ist das gewünschte Seitenverhältnis nicht erreichbar, wird mit schwarzen Rändern eingepasst. Es wird niemals eine Cover-Skalierung verwendet, die die Körperbox abschneiden würde.

Für den resultierenden Quellrahmen `(sx,sy,cw,ch)` und das Zielfenster `(vw,vh)` gilt:

- Skalierung `s = min(vw/cw, vh/ch)`.
- Zusätzlicher Zoom gegenüber Original-Contain: `s / min(vw/sw, vh/sh)`.
- Verschiebung `dx = (vw-cw*s)/2 - sx*s`, `dy = (vh-ch*s)/2 - sy*s`.

`framing()` liefert diese Werte; `drawImage` setzt den unveränderlichen Quellrahmen mit entsprechender Zielgröße um. Die vorhandene Canvas-Pipeline erzeugt ohnehin Trainingsvideo und Aufnahme. Ein zusätzlicher CSS-Transform oder eine zweite Kompositionspipeline wäre hier unnötig. Die Berechnung hängt ausschließlich von gespeicherter Box, Quelldimensionen und festem Zielfenster ab, nie von der aktuellen Pose oder Wiedergabezeit.

## Cache und Datenschutz

SHA-256 jedes Dateiblocks (4 MiB), anschließend SHA-256 der verketteten Blockhashes. Damit fließt jeder Dateibyte ein, auch wenn Name, Größe und Änderungsdatum gleich bleiben. Schlüssel: Algorithmus-/Modellversion, Ausschnittmodus, Dateigröße, Inhaltsfingerabdruck. Geänderte Bytes, Ausschnitt oder Algorithmus erzwingen eine neue Analyse. Der Fingerabdruck wird bei erneutem Import berechnet; die teure Poseanalyse entfällt bei einem Treffer.

`localStorage` enthält höchstens 20 Einträge mit Schlüssel und normierter Box, keine Bilder, Dateinamen oder Posefolgen. Ein konservatives Erkennungs-Fallback wird ebenfalls gespeichert. Decoder-/Timeoutfehler werden nicht dauerhaft gespeichert. Bei gesperrtem oder vollem Speicher funktioniert das aktuelle Ergebnis im Arbeitsspeicher; erneuter Import kann dann erneut analysieren. Browserdaten löschen entfernt die Ergebnisse; private Fenster können Speicherung einschränken. Alte Versionsschlüssel werden nicht wiederverwendet. Es gibt keine Uploads und keinen neuen Netzwerkzugriff. Die bestehenden Downloads von MediaPipe/WASM über jsDelivr und des Modells von Google bleiben erforderlich.

## Leistung und noch offene Abnahme

Nur ein Analysejob und ein zusätzlicher Referenzdecoder gleichzeitig. Bei Datei-/Ausschnittwechsel wird der alte Job abgebrochen und vor dem nächsten freigegeben. Stop, Tabwechsel und Pagehide brechen ab. Zeitlimits und Abbruch schließen Decoder, Medienereignis-Listener und Objekt-URL. Die Kamera darf während der Voranalyse laufen; ihre vorhandene Hintergrundmasken-Inferenz pausiert währenddessen, die Rohkamera und Darstellung bleiben aktiv. Das synchrone MediaPipe-`detect()` kann die UI für die Dauer eines einzelnen Aufrufs anhalten; Abbruch kann erst danach greifen. Auflösungslimit und Pausen begrenzen die Last, garantieren aber keine Framerate auf jeder Hardware.

Automatisierte Tests verwenden synthetische Posen und echte Chromium-Videodecodierung. Sie belegen Integration und Mathematik, keine reale MediaPipe-Erkennungsqualität. Noch erforderlich: Samsung Galaxy S24+ / Android Chrome über GitHub Pages HTTPS mit echten Clips, Hoch-/Querformat, seitlichen Ausfallschritten, schnellen Armen, Drehungen, verschiedenen Abständen und gleichzeitig laufender Kamera; Analysezeit, Spitzen-Speicher, Einzelinferenzzeit, Wiedergabeflüssigkeit, Musik und Aufnahmen messen. Es stand kein echtes Android-Gerät zur Verfügung. Keine gemessene Android-Performance wird behauptet.

GitHub Pages: Root von `main` erst nach manueller PR-Freigabe veröffentlichen; `index.html` und `src/` gemeinsam bereitstellen, kein Build, Backend, Secret oder kostenpflichtiger Dienst nötig. Der PR selbst veröffentlicht nichts. Versionsziel v1.1.0, kein Tag und kein Release angelegt.
