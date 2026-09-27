import ctypes

LEFT_DOWN, LEFT_UP = 0x0002, 0x0004

class WindowsPointer:
    def __init__(self):
        self.user32, self.pressed = ctypes.windll.user32, False

    def move(self, x, y):
        self.user32.SetCursorPos(round(x * (self.user32.GetSystemMetrics(0) - 1)), round(y * (self.user32.GetSystemMetrics(1) - 1)))

    def press(self):
        if not self.pressed:
            self.user32.mouse_event(LEFT_DOWN, 0, 0, 0, 0); self.pressed = True

    def release(self):
        if self.pressed:
            self.user32.mouse_event(LEFT_UP, 0, 0, 0, 0); self.pressed = False
