import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
ICON_ID = "corpus-querier-data-bird"


class LinuxPackagingTests(unittest.TestCase):
    def test_desktop_entry_uses_fresh_icon_identifier(self):
        desktop = (ROOT / "linux" / "corpus-querier.desktop").read_text(
            encoding="utf-8"
        )
        self.assertIn("Icon=corpus-querier\n", desktop)
        self.assertIn("StartupWMClass=CorpusQuerier\n", desktop)
        self.assertIn("StartupNotify=false\n", desktop)
        self.assertIn("TryExec=corpus-querier\n", desktop)

    def test_build_installs_png_icons_and_fallback(self):
        script = (ROOT / "linux" / "build_linux_packages.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(f'ICON_ID="{ICON_ID}"', script)
        self.assertIn('ICON_ALIASES=(corpus-querier corpus-querier-data-bird CorpusQuerier)', script)
        self.assertIn('$icon_alias.png', script)
        self.assertIn("usr/share/pixmaps", script)
        self.assertIn('ICON_SIZES=(16 24 32 48 64 128 256 512)', script)
        self.assertIn('ln -s "corpus-querier.png"', script)
        self.assertIn('Icon=/usr/share/pixmaps/corpus-querier.png', script)

    def test_every_linux_icon_has_the_expected_dimensions(self):
        for size in (16, 24, 32, 48, 64, 128, 256, 512):
            path = (
                ROOT
                / "assets"
                / "linux-icons"
                / f"{size}x{size}"
                / f"{ICON_ID}.png"
            )
            with Image.open(path) as image:
                self.assertEqual(image.size, (size, size))
                self.assertEqual(image.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
