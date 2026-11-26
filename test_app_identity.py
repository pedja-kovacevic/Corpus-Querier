import unittest

from app_identity import (
    APP_VERSION,
    PeckingBird,
    _SIDEBAR_DARK,
    _load_bird_layer,
    _render_pecking_frame,
)


class AppIdentityTests(unittest.TestCase):
    def test_release_version(self):
        self.assertEqual(APP_VERSION, "3.3.0")

    def test_bird_layer_is_nonempty_rgba(self):
        image = _load_bird_layer()
        self.assertEqual(image.mode, "RGBA")
        self.assertIsNotNone(image.getbbox())
        self.assertGreater(image.width, image.height // 2)

    def test_animation_tilts_instead_of_moving_vertically(self):
        angles = PeckingBird._ANGLES
        self.assertGreater(angles[0], 0.0)
        self.assertLess(min(angles), 0.0)
        self.assertGreater(max(angles) - min(angles), 10.0)
        self.assertGreaterEqual(angles.count(min(angles)), 2)

    def test_rendered_frames_are_seamless_with_sidebar(self):
        rest = _render_pecking_frame(0.0, False, _SIDEBAR_DARK)
        contact = _render_pecking_frame(-8.0, True, _SIDEBAR_DARK)
        self.assertEqual(rest.getpixel((0, 0)), _SIDEBAR_DARK)
        self.assertEqual(contact.getpixel((209, 204)), _SIDEBAR_DARK)
        self.assertNotEqual(rest.tobytes(), contact.tobytes())


if __name__ == "__main__":
    unittest.main()
