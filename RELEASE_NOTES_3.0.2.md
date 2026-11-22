# Corpus Querier 3.0.2

This maintenance release installs the approved Corpus Querier data-bird
artwork consistently across Linux, Windows and macOS.

## Linux icon fix

- Preserves the approved halfway-down pecking pose over one flat corpus surface.
- Gives the data-bird artwork a new, unique Linux icon identifier:
  `corpus-querier-data-bird`.
- Installs optimized PNG icons at every standard size from 16 to 512 pixels in
  the hicolor icon theme.
- Installs a PNG in `/usr/share/pixmaps` as a compatibility fallback.
- Uses the same fresh identifier in the Debian launcher and AppImage.
- Retains the Linux window-class association and automatic cache refresh from
  version 3.0.1.

The Windows executable/installer and both macOS application packages use the
same approved artwork.

Application behavior is unchanged. CLARIN.SI and RNC queries still perform at
least two complete attempts.

## Downloads

- **Windows:** `Corpus-Querier-Setup.exe`
- **Linux (Debian/Ubuntu/MX Linux):** `corpus-querier_3.0.2_amd64.deb`
- **Linux portable:** `Corpus-Querier-x86_64.AppImage`
- **macOS Apple Silicon:** `Corpus-Querier-macOS-arm64.dmg`
- **macOS Intel:** `Corpus-Querier-macOS-x86_64.dmg`

**Full changelog:** https://github.com/pedja-kovacevic/Corpus-Querier-CLARIN/compare/v3.0.1...v3.0.2
