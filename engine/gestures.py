import math

def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def classify_hand(landmarks):
    wrist = landmarks[0]
    extended = sum(_distance(wrist, landmarks[tip]) > _distance(wrist, landmarks[pip]) * 1.18 for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)))
    return "open" if extended >= 3 else "fist" if extended <= 1 else "neutral"

class GestureState:
    def __init__(self, stable_frames=3):
        self.stable_frames = stable_frames
        self.current = "none"
        self.candidate = "none"
        self.frames = 0

    def update(self, next_gesture):
        if next_gesture == "neutral": return None
        if next_gesture != self.candidate:
            self.candidate, self.frames = next_gesture, 1
            return None
        self.frames += 1
        if self.frames < self.stable_frames or next_gesture == self.current: return None
        previous, self.current = self.current, next_gesture
        return previous, self.current
