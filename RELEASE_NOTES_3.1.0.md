# Corpus Querier 3.1.0

Corpus Querier 3.1.0 is the first stable release to combine three corpus
providers in one cross-platform desktop application.

## Providers

- **NoSketch Engine** for CLARIN.SI-hosted Bonito corpora;
- **Sketch Engine** through the authenticated official API, with the British
  National Corpus configured as the default starting point;
- **Russian National Corpus** through its official public API.

## Changes since 3.0.2

- added the tested Sketch Engine API module;
- retained mandatory repeated query attempts and highest-valid-result logic;
- distinguished confirmed RNC zero-hit responses from genuine errors;
- added regression tests for explicit zeroes, omitted zero counts and malformed
  responses;
- renamed the first provider card to **NoSketch Engine**;
- enlarged the in-app data bird and added a subtle run-only pecking animation;
- added a brief contact-point pulse synchronized with the bird's beak;
- updated Windows, Linux and macOS package metadata to version 3.1.0.

## RNC zero-result rule

An explicit `wordUsageCount: 0` is always a valid result. If the count is
omitted, Corpus Querier records zero only when the successful JSON response
also contains an empty concordance and an explicit zero text/document/page
signal. Ambiguous or malformed responses remain `ERROR`.

## Downloads

- Windows installer: `Corpus-Querier-Setup.exe`
- Linux Debian package: `corpus-querier_3.1.0_amd64.deb`
- Linux portable AppImage: `Corpus-Querier-x86_64.AppImage`
- macOS Apple Silicon: `Corpus-Querier-macOS-arm64.dmg`
- macOS Intel: `Corpus-Querier-macOS-x86_64.dmg`

The installers include all Python dependencies. End users do not need Python,
PowerShell, Visual Studio Code or a terminal.
