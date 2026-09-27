from dataclasses import asdict, dataclass

@dataclass
class EngineConfig:
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 360
    active_margin: float = 0.12
    smoothing_floor: float = 0.28
    smoothing_boost: float = 3.4
    gesture_frames: int = 3
    lost_hand_release_seconds: float = 0.35

    def update(self, values):
        for key, value in values.items():
            if hasattr(self, key):
                setattr(self, key, type(getattr(self, key))(value))

    def json(self):
        return asdict(self)
