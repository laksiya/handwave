import ctypes

LEFT_DOWN, LEFT_UP, RIGHT_DOWN, RIGHT_UP, WHEEL = 0x0002, 0x0004, 0x0008, 0x0010, 0x0800

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

    def click(self):
        self.user32.mouse_event(LEFT_DOWN, 0, 0, 0, 0); self.user32.mouse_event(LEFT_UP, 0, 0, 0, 0)

    def right_click(self):
        self.user32.mouse_event(RIGHT_DOWN, 0, 0, 0, 0); self.user32.mouse_event(RIGHT_UP, 0, 0, 0, 0)

    def scroll(self, amount):
        self.user32.mouse_event(WHEEL, 0, 0, int(amount * 960), 0)
