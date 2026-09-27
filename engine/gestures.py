import math

def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def _extended(landmarks, tip, pip):
    wrist = landmarks[0]
    return _distance(wrist, landmarks[tip]) > _distance(wrist, landmarks[pip]) * 1.18

def classify_hand(landmarks):
    palm_width = max(0.05, _distance(landmarks[5], landmarks[17]))
    index_pinch = _distance(landmarks[4], landmarks[8]) / palm_width
    middle_pinch = _distance(landmarks[4], landmarks[12]) / palm_width
    if min(index_pinch, middle_pinch) < 0.34:
        return "index_pinch" if index_pinch <= middle_pinch else "middle_pinch"
    index, middle, ring, pinky = (_extended(landmarks, tip, pip) for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)))
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
        self.pinch_started, self.dragging, self.scroll_y = None, False, None

    def reset(self):
        was_dragging = self.dragging
        self.dragging, self.pinch_started, self.scroll_y = False, None, None
        self.state = GestureState(self.state.stable_frames)
        return ["release"] if was_dragging else []

    def update(self, pose, now, vertical_position):
        actions = []
        transition = self.state.update(pose)
        if transition:
            previous, current = transition
            if previous == "index_pinch":
                actions.append("release" if self.dragging else "click")
                self.dragging, self.pinch_started = False, None
            elif previous == "middle_pinch": actions.append("right_click")
            if current == "index_pinch": self.pinch_started = now
            self.scroll_y = vertical_position if current == "scroll" else None
        if self.state.current == "index_pinch" and self.pinch_started is not None and not self.dragging and now - self.pinch_started >= self.drag_hold:
            self.dragging = True; actions.append("press")
        if self.state.current == "scroll":
            if self.scroll_y is not None:
                delta = self.scroll_y - vertical_position
                if abs(delta) >= 0.008: actions.append(("scroll", delta)); self.scroll_y = vertical_position
            else: self.scroll_y = vertical_position
        else: self.scroll_y = None
        raw_pinch = pose in ("index_pinch", "middle_pinch")
        return self.state.current, (self.state.current == "point" and not raw_pinch) or self.dragging, actions
