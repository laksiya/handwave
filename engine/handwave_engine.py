import base64, json, queue, sys, threading, time
import cv2
import mediapipe as mp
from config import EngineConfig
from gestures import GestureController, classify_hand
from pointer_win32 import WindowsPointer
from tracking import AdaptivePointer

def emit(event, **data): print(json.dumps({"event": event, **data}), flush=True)

def encode_preview(frame, landmarks, pose):
    preview = cv2.flip(frame, 1)
    height, width = preview.shape[:2]
    if landmarks:
        index = landmarks[8]
        index_center = (int((1 - index[0]) * width), int(index[1] * height))
        cv2.circle(preview, index_center, 12, (66, 255, 217), -1)
        cv2.circle(preview, index_center, 12, (21, 18, 23), 2)
        if pose == "index_pinch":
            thumb = landmarks[4]
            thumb_center = (int((1 - thumb[0]) * width), int(thumb[1] * height))
            cv2.circle(preview, thumb_center, 12, (246, 105, 65), -1)
            cv2.circle(preview, thumb_center, 12, (21, 18, 23), 2)
        elif pose in ("scroll", "middle_pinch"):
            middle = landmarks[12]
            middle_center = (int((1 - middle[0]) * width), int(middle[1] * height))
            cv2.circle(preview, middle_center, 12, (246, 105, 65), -1)
            cv2.circle(preview, middle_center, 12, (21, 18, 23), 2)
    small = cv2.resize(preview, (320, 180), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 62])
    return base64.b64encode(encoded).decode('ascii') if ok else None

class FreshFrameCamera:
    def __init__(self, config):
        self.capture = cv2.VideoCapture(config.camera_index, cv2.CAP_DSHOW)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width); self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
        self.capture.set(cv2.CAP_PROP_FPS, 30); self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.frame, self.lock, self.running = None, threading.Lock(), self.capture.isOpened()
        if self.running: threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        while self.running:
            ok, frame = self.capture.read()
            if ok:
                with self.lock: self.frame = frame
            else: time.sleep(0.005)

    def latest(self):
        with self.lock: return None if self.frame is None else self.frame.copy()

    def close(self): self.running = False; self.capture.release()

class TrackingEngine:
    def __init__(self):
        self.config, self.commands, self.running, self.paused = EngineConfig(), queue.Queue(), True, False
        self.pointer, self.smoother, self.gesture, self.last_hand = WindowsPointer(), AdaptivePointer(), GestureController(), 0.0

    def command_reader(self):
        for line in sys.stdin:
            try: self.commands.put(json.loads(line))
            except json.JSONDecodeError: pass
        self.commands.put({"command": "stop"})

    def apply_commands(self):
        while True:
            try: message = self.commands.get_nowait()
            except queue.Empty: return
            command = message.get("command")
            if command == "stop": self.running = False
            elif command == "pause": self.paused = True; self.pointer.release(); self.gesture.reset(); emit("paused")
            elif command == "resume": self.paused = False; emit("resumed")
            elif command == "configure":
                self.config.update(message.get("values", {})); self.smoother.configure(self.config.active_margin, self.config.smoothing_floor, self.config.smoothing_boost); self.gesture.state.stable_frames = max(2, self.config.gesture_frames); emit("configured", config=self.config.json())

    def run(self):
        threading.Thread(target=self.command_reader, daemon=True).start(); camera = FreshFrameCamera(self.config)
        if not camera.running: emit("fault", message="Camera could not start. Close other camera apps and retry."); return 2
        hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=1, model_complexity=0, min_detection_confidence=0.55, min_tracking_confidence=0.55)
        emit("ready", config=self.config.json()); frame_count = 0; fps_started = last_status = last_preview = time.perf_counter()
        try:
            while self.running:
                self.apply_commands(); frame = camera.latest()
                if self.paused or frame is None: time.sleep(0.008); continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); rgb.flags.writeable = False; result = hands.process(rgb); now = time.perf_counter(); frame_count += 1
                detected_hands = result.multi_hand_landmarks or []
                landmarks = None
                current = self.gesture.state.current
                if detected_hands:
                    landmarks = [(p.x, p.y, p.z) for p in detected_hands[0].landmark]
                    raw_x, raw_y = landmarks[8][0], landmarks[8][1]
                    current, should_move, actions = self.gesture.update(classify_hand(landmarks), now, raw_y)
                    if should_move:
                        screen_x, screen_y = self.smoother.update(1 - raw_x, raw_y); self.pointer.move(screen_x, screen_y)
                    for action in actions:
                        if action == "click": self.pointer.click()
                        elif action == "right_click": self.pointer.right_click()
                        elif action == "press": self.pointer.press()
                        elif action == "release": self.pointer.release()
                        elif isinstance(action, tuple) and action[0] == "scroll": self.pointer.scroll(action[1])
                    self.last_hand = now
                elif now - self.last_hand > self.config.lost_hand_release_seconds:
                    for action in self.gesture.reset():
                        if action == "release": self.pointer.release()
                if now - last_preview >= 0.10:
                    image = encode_preview(frame, landmarks, current)
                    if image: emit("preview", image=image)
                    last_preview = now
                if now - last_status >= 1.0:
                    emit("tracking", fps=round(frame_count / (now - fps_started), 1), gesture=self.gesture.state.current, hand=bool(detected_hands)); last_status = now
        finally:
            self.pointer.release(); hands.close(); camera.close(); emit("stopped")
        return 0

if __name__ == "__main__": raise SystemExit(TrackingEngine().run())
