import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ICON_ID = "corpus-querier-data-bird"


class LinuxPackagingTests(unittest.TestCase):
    def test_desktop_entry_uses_fresh_icon_identifier(self):
        desktop = (ROOT / "linux" / "corpus-querier.desktop").read_text(
            encoding="utf-8"
        )
        self.assertIn(f"Icon={ICON_ID}\n", desktop)
        self.assertIn("StartupWMClass=CorpusQuerier\n", desktop)

    def test_build_installs_svg_and_png_fallback(self):
        script = (ROOT / "linux" / "build_linux_packages.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(f"{ICON_ID}.svg", script)
        self.assertIn(f"{ICON_ID}.png", script)
        self.assertIn("usr/share/pixmaps", script)
        self.assertIn(f"ln -s {ICON_ID}.svg", script)


if __name__ == "__main__":
    unittest.main()
