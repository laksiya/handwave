import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "engine"))

from gestures import GestureController, GestureState, classify_hand
from tracking import AdaptivePointer
from handwave_engine import encode_preview


def hand(*extended):
    points = [(0.5, 0.8, 0.0) for _ in range(21)]
    points[4], points[5], points[17] = (0.2, 0.7, 0.0), (0.4, 0.55, 0.0), (0.6, 0.55, 0.0)
    for name, tip, pip, x in (("index", 8, 6, 0.44), ("middle", 12, 10, 0.49), ("ring", 16, 14, 0.54), ("pinky", 20, 18, 0.59)):
        points[pip] = (x, 0.55, 0.0)
        points[tip] = (x, 0.2 if name in extended else 0.65, 0.0)
    return points

def pinched(finger):
    points = hand("index")
    tip = 8 if finger == "index" else 12
    points[tip] = (0.30, 0.50, 0.0)
    points[4] = (0.305, 0.505, 0.0)
    return points


class GestureTests(unittest.TestCase):
    def test_recommended_pose_classification(self):
        self.assertEqual(classify_hand(hand("index")), "point")
        self.assertEqual(classify_hand(hand("index", "middle")), "scroll")
        self.assertEqual(classify_hand(hand("index", "middle", "ring", "pinky")), "open")
        self.assertEqual(classify_hand(hand()), "fist")
        self.assertEqual(classify_hand(pinched("index")), "index_pinch")
        self.assertEqual(classify_hand(pinched("middle")), "middle_pinch")

    def test_transition_requires_stable_frames(self):
        state = GestureState(stable_frames=3)
        self.assertIsNone(state.update("fist"))
        self.assertIsNone(state.update("fist"))
        self.assertEqual(state.update("fist"), ("none", "fist"))

    def test_quick_index_pinch_clicks_and_held_pinch_drags(self):
        controller = GestureController(stable_frames=2, drag_hold=0.28)
        controller.update("index_pinch", 0.00, 0.5)
        controller.update("index_pinch", 0.02, 0.5)
        controller.update("point", 0.12, 0.5)
        _, _, actions = controller.update("point", 0.14, 0.5)
        self.assertIn("click", actions)
        controller.update("index_pinch", 1.00, 0.5)
        controller.update("index_pinch", 1.02, 0.5)
        _, moving, actions = controller.update("index_pinch", 1.31, 0.5)
        self.assertTrue(moving)
        self.assertIn("press", actions)

    def test_raw_pinch_freezes_cursor_before_confirmation(self):
        controller = GestureController(stable_frames=3)
        controller.update("point", 0.00, 0.5)
        controller.update("point", 0.02, 0.5)
        controller.update("point", 0.04, 0.5)
        _, moving, _ = controller.update("index_pinch", 0.06, 0.62)
        self.assertFalse(moving)


class PointerTests(unittest.TestCase):
    def test_active_area_maps_to_full_screen(self):
        pointer = AdaptivePointer(margin=0.12, floor=1.0, boost=0.0)
        self.assertEqual(pointer.update(0.12, 0.12), (0.0, 0.0))
        pointer = AdaptivePointer(margin=0.12, floor=1.0, boost=0.0)
        self.assertEqual(pointer.update(0.88, 0.88), (1.0, 1.0))

    def test_preview_encodes_tracked_hand_overlay(self):
        frame = np.zeros((180, 320, 3), dtype=np.uint8)
        scroll_image = encode_preview(frame, hand("index", "middle"), "scroll")
        pinch_image = encode_preview(frame, pinched("index"), "index_pinch")
        self.assertGreater(len(scroll_image), 100)
        self.assertGreater(len(pinch_image), 100)


if __name__ == "__main__":
    unittest.main()
