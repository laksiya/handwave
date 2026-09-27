import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "engine"))

from gestures import GestureState, classify_hand
from tracking import AdaptivePointer


def hand(open_hand):
    points = [(0.5, 0.8, 0.0)] * 21
    points = list(points)
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        points[pip] = (0.5, 0.55, 0.0)
        points[tip] = (0.5, 0.2 if open_hand else 0.65, 0.0)
    return points


class GestureTests(unittest.TestCase):
    def test_open_and_fist_classification(self):
        self.assertEqual(classify_hand(hand(True)), "open")
        self.assertEqual(classify_hand(hand(False)), "fist")

    def test_transition_requires_stable_frames(self):
        state = GestureState(stable_frames=3)
        self.assertIsNone(state.update("fist"))
        self.assertIsNone(state.update("fist"))
        self.assertEqual(state.update("fist"), ("none", "fist"))


class PointerTests(unittest.TestCase):
    def test_active_area_maps_to_full_screen(self):
        pointer = AdaptivePointer(margin=0.12, floor=1.0, boost=0.0)
        self.assertEqual(pointer.update(0.12, 0.12), (0.0, 0.0))
        pointer = AdaptivePointer(margin=0.12, floor=1.0, boost=0.0)
        self.assertEqual(pointer.update(0.88, 0.88), (1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
