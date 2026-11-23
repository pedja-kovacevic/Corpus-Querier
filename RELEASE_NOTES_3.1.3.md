# Corpus Querier 3.1.3

Corpus Querier 3.1.3 corrects Linux launcher and running-window icon discovery.
It contains all RNC zero-result and resume fixes from 3.1.2.

## Linux icon correction

- the desktop entry no longer falsely declares support for the freedesktop
  startup-notification completion protocol;
- the Debian launcher uses an absolute `/usr/share/pixmaps` fallback permitted
  by the desktop-entry specification;
- the bird is installed under `corpus-querier`, `corpus-querier-data-bird` and
  `CorpusQuerier` aliases at every standard icon size;
- GTK and XDG icon caches are refreshed after installation and removal;
- the Tk window icon is reapplied after the X11 window is mapped, preventing a
  panel from retaining the generic Tk/PyInstaller mark;
- the AppImage keeps its root icon, `.DirIcon`, theme icons and pixmap fallback.

## Downloads

- Windows: `Corpus-Querier-Setup.exe`
- Linux: `corpus-querier_3.1.3_amd64.deb`
- Linux portable: `Corpus-Querier-x86_64.AppImage`
- macOS Apple Silicon: `Corpus-Querier-macOS-arm64.dmg`
- macOS Intel: `Corpus-Querier-macOS-x86_64.dmg`
