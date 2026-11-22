# Corpus Querier 3.0.1

This maintenance release corrects the Linux packaging of Corpus Querier 3.

## Fixes

- Includes Pillow's dynamically loaded Tkinter bridge in the standalone Linux
  executable. This prevents the launcher from crashing while displaying the
  data-bird image.
- Associates the Linux window with the Corpus Querier desktop entry so the
  correct icon appears in application menus, docks and task switchers.
- Refreshes the desktop-entry and icon caches when the Debian package is
  installed or removed.
- Adds the standard `.DirIcon` link to the AppImage.

All Corpus Querier 3 features and query behavior are otherwise unchanged.
Every corpus query still performs at least two complete attempts.

## Downloads

- **Windows:** `Corpus-Querier-Setup.exe`
- **Linux (Debian/Ubuntu/MX Linux):** `corpus-querier_3.0.1_amd64.deb`
- **Linux portable:** `Corpus-Querier-x86_64.AppImage`
- **macOS Apple Silicon:** `Corpus-Querier-macOS-arm64.dmg`
- **macOS Intel:** `Corpus-Querier-macOS-x86_64.dmg`

The packaged applications include their Python dependencies. Python and a
development environment are not required.

**Full changelog:** https://github.com/pedja-kovacevic/Corpus-Querier-CLARIN/compare/v3.0.0...v3.0.1
