import math

def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def _extended(landmarks, mcp, pip, tip):
    first = (landmarks[mcp][0] - landmarks[pip][0], landmarks[mcp][1] - landmarks[pip][1])
    second = (landmarks[tip][0] - landmarks[pip][0], landmarks[tip][1] - landmarks[pip][1])
    length = max(1e-6, math.hypot(*first) * math.hypot(*second))
    cosine = max(-1.0, min(1.0, (first[0] * second[0] + first[1] * second[1]) / length))
    return math.degrees(math.acos(cosine)) > 145

def classify_hand(landmarks):
    palm_width = max(0.05, _distance(landmarks[5], landmarks[17]))
    index_pinch = _distance(landmarks[4], landmarks[8]) / palm_width
    middle_pinch = _distance(landmarks[4], landmarks[12]) / palm_width
    if min(index_pinch, middle_pinch) < 0.42:
        return "index_pinch" if index_pinch <= middle_pinch else "middle_pinch"
    index, middle, ring, pinky = (_extended(landmarks, mcp, pip, tip) for mcp, pip, tip in ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)))
    if index and not middle and not ring and not pinky: return "point"
    if index and middle and not ring and not pinky: return "scroll"
    if sum((index, middle, ring, pinky)) >= 3: return "open"
    if not any((index, middle, ring, pinky)): return "fist"
    return "neutral"

class GestureState:
    def __init__(self, stable_frames=2):
        self.stable_frames, self.current, self.candidate, self.frames = stable_frames, "none", "none", 0

    def update(self, next_gesture):
        if next_gesture == "neutral": return None
        if next_gesture != self.candidate:
            self.candidate, self.frames = next_gesture, 1
            return None
        self.frames += 1
        if self.frames < self.stable_frames or next_gesture == self.current: return None
        previous, self.current = self.current, next_gesture
        return previous, self.current

class GestureController:
    def __init__(self, stable_frames=2, drag_hold=0.28):
        self.state, self.drag_hold = GestureState(stable_frames), drag_hold
        self.pinch_started, self.dragging, self.scroll_y, self.last_scroll_at = None, False, None, 0.0

    def reset(self):
        was_pressed = self.state.current == "index_pinch"
        self.dragging, self.pinch_started, self.scroll_y = False, None, None
        self.state = GestureState(self.state.stable_frames)
        return ["release"] if was_pressed else []

    def update(self, pose, now, vertical_position, scroll_direction=0):
        actions = []
        transition = self.state.update(pose)
        if transition:
            previous, current = transition
            if previous == "index_pinch":
                actions.append("release")
                self.dragging, self.pinch_started = False, None
            elif previous == "middle_pinch": actions.append("right_click")
            if current == "index_pinch":
                self.pinch_started = now
                actions.append("press")
            self.scroll_y = vertical_position if current == "scroll" else None
        if self.state.current == "index_pinch" and self.pinch_started is not None and not self.dragging and now - self.pinch_started >= self.drag_hold:
            self.dragging = True
        if self.state.current == "scroll":
            if scroll_direction and now - self.last_scroll_at >= 0.08:
                actions.append(("scroll", scroll_direction * 0.12))
                self.last_scroll_at = now
        else: self.scroll_y = None
        raw_pinch = pose in ("index_pinch", "middle_pinch")
        return self.state.current, (self.state.current == "point" and not raw_pinch) or self.dragging, actions

def scroll_orientation(landmarks):
    tip_y = (landmarks[8][1] + landmarks[12][1]) / 2
    pip_y = (landmarks[6][1] + landmarks[10][1]) / 2
    return 1 if tip_y > pip_y else -1
