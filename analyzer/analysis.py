"""Streaming quality aggregation and one conservative crop for the entire clip."""
import math


class Quality:
    def __init__(self):
        self.warnings = []
        self.missing = 0
        self.events = {}
        self.bounds = [1., 1., 0., 0.]
        self.safe = True
        self.previous = None

    def warn(self, text):
        if text not in self.warnings and len(self.warnings) < 90:
            self.warnings.append(text[:500])

    def observe(self, timestamp, missing, points, people):
        self.missing += missing
        labels = []
        if self.previous is not None and timestamp-self.previous > .5:
            labels.append('Zeitlücke über 0,5 s zwischen Analyseframes')
        self.previous = timestamp
        if people > 1:
            labels.append('Mehrere Personen: keine eindeutige Zuordnung')
        if missing:
            labels.append('Fehlende/ungültige Gelenke')
        if len(points) != 33:
            labels.append('Verdeckung oder geringe Konfidenz')
        if any(x < .02 or x > .98 or y < .02 or y > .98 for x, y in points):
            labels.append('Körper nahe Bildrand; Abschneiden möglich')
        for label in labels:
            count, start, _ = self.events.get(label, (0, timestamp, timestamp))
            self.events[label] = (count + 1, start, timestamp)
        if labels:
            self.safe = False
        for x, y in points:
            self.bounds = [min(self.bounds[0], x), min(self.bounds[1], y),
                           max(self.bounds[2], x), max(self.bounds[3], y)]

    def zoom(self, width, height, aspect):
        result = dict(mode='fixed', x=0., y=0., width=1., height=1., targetAspectRatio=aspect)
        x0, y0, x1, y1 = self.bounds
        if not self.safe or x1 <= x0 or y1 <= y0:
            self.warn('Zoom-Fallback: Originalbild wegen unsicherer Ganzkörpergrenzen.')
            return result
        # Union over ALL analyzed frames, 8% reserve and additional crown reserve.
        bw, bh = x1-x0, y1-y0
        x0, x1 = max(0., x0-.08*bw), min(1., x1+.08*bw)
        y0, y1 = max(0., y0-.13*bh), min(1., y1+.08*bh)
        cw, ch = x1-x0, y1-y0
        ratio = cw*width/(ch*height)
        if ratio < aspect:
            cw = min(1., ch*height*aspect/width)
        else:
            ch = min(1., cw*width/aspect/height)
        x = min(max(0., (x0+x1-cw)/2), 1.-cw)
        y = min(max(0., (y0+y1-ch)/2), 1.-ch)
        result.update(x=x, y=y, width=cw, height=ch)
        return result

    def report(self):
        warnings = list(self.warnings)
        for label, (count, start, end) in self.events.items():
            warnings.append(f'{label}: {count} Analyseframes, erster/letzter Zeitpunkt {start:.3f}–{end:.3f} s (kein durchgehendes Intervall).')
        return dict(status='partial' if self.missing else 'complete',
                    missingLandmarks=self.missing, warnings=warnings[:100])


class Timeline:
    """Keep original PTS in export; integer milliseconds are only the model clock."""
    def __init__(self, max_fps):
        self.interval = 0 if max_fps == 0 else 1/max_fps
        self.previous = -1.
        self.selected = None
        self.model_ms = -1

    def accept(self, time):
        if time is None or not math.isfinite(time) or time < 0 or time <= self.previous:
            raise ValueError('Video-PTS fehlen, sind negativ oder nicht streng monoton; keine FPS-Ersatztimeline.')
        self.previous = time
        if self.selected is not None and time-self.selected < self.interval-1e-9:
            return False
        self.selected = time
        self.model_ms = max(self.model_ms+1, round(time*1000))
        return True
