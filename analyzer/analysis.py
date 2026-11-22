"""Streaming quality aggregation and one conservative crop for the entire clip."""
import math


class Quality:
    def __init__(self, zoom_max_uncertain_percent=10):
        if not math.isfinite(zoom_max_uncertain_percent) or not 0 <= zoom_max_uncertain_percent <= 100:
            raise ValueError('Zoomtoleranz muss endlich sein und zwischen 0 und 100 Prozent liegen.')
        self.zoom_max_uncertain_percent = zoom_max_uncertain_percent
        self.warnings = []
        self.missing = 0
        self.events = {}
        self.bounds = [1., 1., 0., 0.]
        self.safe = True
        self.previous = None
        self.frames = 0
        self.uncertain_frames = 0
        self.uncertain_start = None
        self.longest_uncertain_seconds = 0.

    def warn(self, text):
        if text not in self.warnings and len(self.warnings) < 90:
            self.warnings.append(text[:500])

    def observe(self, timestamp, missing, points, people):
        self.missing += missing
        labels = []
        if self.previous is not None and timestamp-self.previous > .5:
            labels.append('Zeitlücke über 0,5 s zwischen Analyseframes')
            self.safe = False
        if people > 1:
            labels.append('Mehrere Personen: keine eindeutige Zuordnung')
        if missing:
            labels.append('Fehlende/ungültige Gelenke')
        if len(points) != 33:
            labels.append('Verdeckung oder geringe Konfidenz')
        if any(x < .02 or x > .98 or y < .02 or y > .98 for x, y in points):
            labels.append('Körper nahe Bildrand; Abschneiden möglich')
            self.safe = False
        self.frames += 1
        uncertain = people != 1 or missing > 0 or len(points) != 33
        if uncertain:
            self.uncertain_frames += 1
            if self.uncertain_start is None:
                # Include the last reliable instant in the unobserved interval.
                self.uncertain_start = self.previous if self.previous is not None else timestamp
        if self.uncertain_start is not None:
            self.longest_uncertain_seconds = max(self.longest_uncertain_seconds, timestamp-self.uncertain_start)
            if not uncertain:
                self.uncertain_start = None
        self.previous = timestamp
        for label in labels:
            count, start, _ = self.events.get(label, (0, timestamp, timestamp))
            self.events[label] = (count + 1, start, timestamp)
        # Retain EVERY reliable point, including reliable limbs of partial poses.
        # Tolerance never trims trustworthy extrema or changes stored pose data.
        for x, y in points:
            self.bounds = [min(self.bounds[0], x), min(self.bounds[1], y),
                           max(self.bounds[2], x), max(self.bounds[3], y)]

    def zoom(self, width, height, aspect):
        result = dict(mode='fixed', x=0., y=0., width=1., height=1., targetAspectRatio=aspect)
        x0, y0, x1, y1 = self.bounds
        if self.frames:
            self.warn(f'Zoomprüfung: {self.uncertain_frames}/{self.frames} unsichere Bilder '
                      f'({self.uncertain_frames/self.frames*100:.2f} %), '
                      f'Toleranz {self.zoom_max_uncertain_percent:g} %.')
        over_budget = self.uncertain_frames*100 > self.frames*self.zoom_max_uncertain_percent
        long_gap = self.longest_uncertain_seconds > .5 + 1e-9
        if long_gap:
            self.warn(f'Zoom: zusammenhängende Erkennungsunsicherheit über 0,5 s '
                      f'(maximal {self.longest_uncertain_seconds:.3f} s).')
        if not self.safe or over_budget or long_gap or x1 <= x0 or y1 <= y0:
            self.warn('Zoom-Fallback: Originalbild wegen unsicherer Ganzkörpergrenzen.')
            return result
        # Additional reserve when accepting incomplete/uncertain observations.
        margin = .13 if self.uncertain_frames else .08
        bw, bh = x1-x0, y1-y0
        x0, x1 = max(0., x0-margin*bw), min(1., x1+margin*bw)
        y0, y1 = max(0., y0-(margin+.05)*bh), min(1., y1+margin*bh)
        if self.uncertain_frames:
            self.warn('Zoom trotz kurzer unsicherer Bilder: zusätzliche 5 % Randreserve; '
                      'nicht beobachtete Bewegung kann außerhalb des Ausschnitts liegen.')
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
