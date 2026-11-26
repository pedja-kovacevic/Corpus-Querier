#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-3.3.1}"
if [[ ! "$VERSION" =~ ^[0-9]+([.][0-9]+)*([+-][A-Za-z0-9.]+)?$ ]]; then
  VERSION="3.3.1"
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_BINARY="$PROJECT_ROOT/dist/Corpus Querier"
OUTPUT_DIR="$PROJECT_ROOT/linux-output"
APPDIR="$PROJECT_ROOT/build-linux/Corpus-Querier.AppDir"
DEB_ROOT="$PROJECT_ROOT/build-linux/deb-root"
ICON_ID="corpus-querier-data-bird"
ICON_ALIASES=(corpus-querier corpus-querier-data-bird CorpusQuerier)
ICON_SIZES=(16 24 32 48 64 128 256 512)

if [[ ! -x "$APP_BINARY" ]]; then
  echo "Missing Linux executable: $APP_BINARY" >&2
  echo "Run PyInstaller before this script." >&2
  exit 1
fi

rm -rf "$PROJECT_ROOT/build-linux" "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# AppImage directory
mkdir -p \
  "$APPDIR/usr/bin" \
  "$APPDIR/usr/share/applications" \
  "$APPDIR/usr/share/pixmaps"
install -m 755 "$APP_BINARY" "$APPDIR/usr/bin/corpus-querier"
install -m 755 "$PROJECT_ROOT/linux/AppRun" "$APPDIR/AppRun"
install -m 644 "$PROJECT_ROOT/linux/corpus-querier.desktop" \
  "$APPDIR/corpus-querier.desktop"
install -m 644 "$PROJECT_ROOT/linux/corpus-querier.desktop" \
  "$APPDIR/usr/share/applications/corpus-querier.desktop"
install -m 644 "$PROJECT_ROOT/assets/linux-icons/512x512/$ICON_ID.png" \
  "$APPDIR/corpus-querier.png"
ln -s "corpus-querier.png" "$APPDIR/.DirIcon"
for size in "${ICON_SIZES[@]}"; do
  icon_dir="$APPDIR/usr/share/icons/hicolor/${size}x${size}/apps"
  mkdir -p "$icon_dir"
  for icon_alias in "${ICON_ALIASES[@]}"; do
    install -m 644 \
      "$PROJECT_ROOT/assets/linux-icons/${size}x${size}/$ICON_ID.png" \
      "$icon_dir/$icon_alias.png"
  done
done
for icon_alias in "${ICON_ALIASES[@]}"; do
  install -m 644 "$PROJECT_ROOT/assets/linux-icons/512x512/$ICON_ID.png" \
    "$APPDIR/usr/share/pixmaps/$icon_alias.png"
done

ARCH=x86_64 VERSION="$VERSION" \
  "$PROJECT_ROOT/appimagetool-x86_64.AppImage" --appimage-extract-and-run \
  "$APPDIR" "$OUTPUT_DIR/Corpus-Querier-x86_64.AppImage"
chmod +x "$OUTPUT_DIR/Corpus-Querier-x86_64.AppImage"

# Debian package
mkdir -p \
  "$DEB_ROOT/DEBIAN" \
  "$DEB_ROOT/usr/bin" \
  "$DEB_ROOT/usr/share/applications" \
  "$DEB_ROOT/usr/share/pixmaps" \
  "$DEB_ROOT/usr/share/doc/corpus-querier"
install -m 755 "$APP_BINARY" "$DEB_ROOT/usr/bin/corpus-querier"
sed 's|^Icon=.*|Icon=/usr/share/pixmaps/corpus-querier.png|' \
  "$PROJECT_ROOT/linux/corpus-querier.desktop" \
  > "$DEB_ROOT/usr/share/applications/corpus-querier.desktop"
for size in "${ICON_SIZES[@]}"; do
  icon_dir="$DEB_ROOT/usr/share/icons/hicolor/${size}x${size}/apps"
  mkdir -p "$icon_dir"
  for icon_alias in "${ICON_ALIASES[@]}"; do
    install -m 644 \
      "$PROJECT_ROOT/assets/linux-icons/${size}x${size}/$ICON_ID.png" \
      "$icon_dir/$icon_alias.png"
  done
done
for icon_alias in "${ICON_ALIASES[@]}"; do
  install -m 644 "$PROJECT_ROOT/assets/linux-icons/512x512/$ICON_ID.png" \
    "$DEB_ROOT/usr/share/pixmaps/$icon_alias.png"
done
install -m 644 "$PROJECT_ROOT/LICENSE" \
  "$DEB_ROOT/usr/share/doc/corpus-querier/copyright"
install -m 755 "$PROJECT_ROOT/linux/postinst" "$DEB_ROOT/DEBIAN/postinst"
install -m 755 "$PROJECT_ROOT/linux/postrm" "$DEB_ROOT/DEBIAN/postrm"

sed "s/@VERSION@/$VERSION/g" "$PROJECT_ROOT/linux/control.template" \
  > "$DEB_ROOT/DEBIAN/control"
chmod 644 "$DEB_ROOT/DEBIAN/control"

dpkg-deb --build --root-owner-group "$DEB_ROOT" \
  "$OUTPUT_DIR/corpus-querier_${VERSION}_amd64.deb"

echo "Linux packages created in $OUTPUT_DIR"
