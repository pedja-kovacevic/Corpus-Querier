import unittest

from app_identity import APP_VERSION, PeckingBird, _load_bird_layer


class AppIdentityTests(unittest.TestCase):
    def test_release_version(self):
        self.assertEqual(APP_VERSION, "3.1.0")

    def test_bird_layer_is_nonempty_rgba(self):
        image = _load_bird_layer()
        self.assertEqual(image.mode, "RGBA")
        self.assertIsNotNone(image.getbbox())
        self.assertGreater(image.width, image.height // 2)

    def test_animation_has_rest_lift_and_contact_frames(self):
        positions = PeckingBird._POSITIONS
        self.assertLess(min(positions), PeckingBird._REST_Y)
        self.assertEqual(max(positions), PeckingBird._CONTACT_Y)
        self.assertGreaterEqual(positions.count(PeckingBird._CONTACT_Y), 2)


if __name__ == "__main__":
    unittest.main()
