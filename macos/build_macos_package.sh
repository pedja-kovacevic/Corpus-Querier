#!/usr/bin/env bash
set -euo pipefail

ARCHITECTURE="${1:?Usage: build_macos_package.sh <arm64|x86_64>}"
case "$ARCHITECTURE" in
  arm64|x86_64) ;;
  *)
    echo "Unsupported macOS architecture: $ARCHITECTURE" >&2
    exit 1
    ;;
esac

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_BUNDLE="$PROJECT_ROOT/dist/Corpus Querier.app"
OUTPUT_DIR="$PROJECT_ROOT/macos-output"
OUTPUT_FILE="$OUTPUT_DIR/Corpus-Querier-macOS-$ARCHITECTURE.dmg"

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "Missing macOS application bundle: $APP_BUNDLE" >&2
  echo "Run PyInstaller on macOS before this script." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/corpus-querier.XXXXXX")"
trap 'rm -rf "$STAGING_DIR"' EXIT

ditto "$APP_BUNDLE" "$STAGING_DIR/Corpus Querier.app"
ln -s /Applications "$STAGING_DIR/Applications"
hdiutil create \
  -volname "Corpus Querier" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$OUTPUT_FILE"

echo "macOS package created: $OUTPUT_FILE"
