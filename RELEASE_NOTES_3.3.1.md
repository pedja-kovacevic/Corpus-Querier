# Corpus Querier 3.3.1

Version 3.3.1 is a small provider-specific maintenance release.

## Change

- In the NoSketch Engine module, selecting **Resume** during an automatic
  rate-limit pause now continues the run immediately and starts a fresh local
  request count.
- Authenticated Sketch Engine limits remain strict: an early manual Resume
  rechecks the rolling request windows and cannot override the configured
  reserve.
- The Russian National Corpus module is unchanged.

The change uses the existing Pause/Resume control; no additional button or
main-screen option has been added.

Installers are provided for Windows, Linux, macOS Intel and macOS Apple
Silicon.
