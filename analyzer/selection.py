"""Conservative temporal selection for explicitly confirmed one-person footage."""
from dataclasses import dataclass
import math
from types import SimpleNamespace


@dataclass
class Selection:
    result: object
    index: int | None
    candidates: int
    status: str


def empty_pose():
    return SimpleNamespace(pose_landmarks=[], pose_world_landmarks=[])


class PersonSelector:
    """Prefer a distinct foreground figure, then track position and scale.

    Extra detections are hypotheses, never claimed to be proven reflections.
    Ambiguous matches are rejected rather than silently changing identities.
    """
    def __init__(self):
        self.previous = None
        self.last_seen = None

    @staticmethod
    def describe(landmarks):
        if len(landmarks) != 33:
            return None
        points = []
        torso = []
        for index, point in enumerate(landmarks):
            values = (point.x, point.y, getattr(point, 'visibility', None), getattr(point, 'presence', None))
            if not all(isinstance(v, (int,float)) and math.isfinite(v) for v in values):
                continue
            if not all(0 <= v <= 1 for v in values) or min(values[2:]) < .5:
                continue
            points.append(values[:2])
            if index in (11,12,23,24):
                torso.append(values[:2])
        if len(torso) < 3 or len(points) < 8:
            return None
        xs, ys = zip(*points)
        area = (max(xs)-min(xs))*(max(ys)-min(ys))
        if area < .002:
            return None
        cx = sum(p[0] for p in torso)/len(torso)
        cy = sum(p[1] for p in torso)/len(torso)
        return cx, cy, math.sqrt(area), area

    def select(self, result, timestamp):
        count = len(result.pose_landmarks)
        candidates = []
        for index, image in enumerate(result.pose_landmarks):
            if index >= len(result.pose_world_landmarks) or len(result.pose_world_landmarks[index]) != 33:
                continue
            description = self.describe(image)
            if description is not None:
                candidates.append((index, description))
        if not candidates:
            return Selection(empty_pose(), None, count, 'missing')
        fresh = self.previous is None or timestamp-self.last_seen > .75
        if fresh:
            ordered = sorted(candidates, key=lambda c: c[1][3], reverse=True)
            if len(ordered)>1 and ordered[0][1][3] < 1.8*ordered[1][1][3]:
                return Selection(empty_pose(), None, count, 'ambiguous')
            chosen = ordered[0]
            status = 'initial' if self.previous is None else 'reacquired'
        else:
            def distance(candidate):
                cx, cy, scale, _ = candidate[1]
                px, py, previous_scale, _ = self.previous
                return math.hypot(cx-px, cy-py)/max(previous_scale,scale,.05) + .3*abs(math.log(scale/previous_scale))
            ordered = sorted(candidates, key=distance)
            best = distance(ordered[0])
            if best > min(1.2, .6+timestamp-self.last_seen):
                return Selection(empty_pose(), None, count, 'jump_rejected')
            if len(ordered)>1 and distance(ordered[1])-best < .2:
                return Selection(empty_pose(), None, count, 'ambiguous')
            chosen, status = ordered[0], 'tracked'
        index, self.previous = chosen
        self.last_seen = timestamp
        selected = SimpleNamespace(pose_landmarks=[result.pose_landmarks[index]],
                                   pose_world_landmarks=[result.pose_world_landmarks[index]])
        return Selection(selected, index, count, status)
