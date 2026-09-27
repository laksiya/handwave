import math

class AdaptivePointer:
    def __init__(self, margin=0.12, floor=0.28, boost=3.4):
        self.margin, self.floor, self.boost = margin, floor, boost
        self.x = self.y = None

    def configure(self, margin, floor, boost):
        self.margin, self.floor, self.boost = margin, floor, boost

    def update(self, raw_x, raw_y):
        if self.x is None: self.x, self.y = raw_x, raw_y
        else:
            speed = math.hypot(raw_x - self.x, raw_y - self.y)
            alpha = min(0.92, self.floor + speed * self.boost)
            self.x += (raw_x - self.x) * alpha
            self.y += (raw_y - self.y) * alpha
        span = max(0.1, 1 - self.margin * 2)
        return max(0.0, min(1.0, (self.x - self.margin) / span)), max(0.0, min(1.0, (self.y - self.margin) / span))

def palm_center(landmarks):
    points = [landmarks[index] for index in (0, 5, 9, 13, 17)]
    return sum(point[0] for point in points) / 5, sum(point[1] for point in points) / 5
