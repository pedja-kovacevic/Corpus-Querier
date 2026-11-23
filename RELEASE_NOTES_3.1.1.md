# Corpus Querier 3.1.1

Corpus Querier 3.1.1 is a corrective release for the RNC transport layer and
the in-app data-bird animation. It retains the three providers introduced in
3.1.0: NoSketch Engine, Sketch Engine and the Russian National Corpus.

## RNC reliability correction

- connection resets, timeouts and retryable HTTP failures no longer consume
  one of the two required corpus-query attempts;
- the failed socket pool is discarded after a connection reset;
- the same required attempt is retried with interruptible backoff at
  2, 5, 10, 20, 30, 60, 120 and then 300 seconds;
- HTTP 429 responses respect the server's `Retry-After` value when supplied;
- persistent remote connection refusals pause on the same cell instead of
  filling subsequent spreadsheet cells with false `ERROR` values;
- a query is accepted only after the configured number of successful corpus
  responses has been received;
- confirmed zero-hit responses remain valid zeroes, while malformed or
  ambiguous responses remain errors.

## Bird animation correction

- the bird now tilts forward around a fixed lower-body pivot and returns to its
  resting pose instead of moving vertically;
- the data platform remains completely stationary;
- each frame is rendered on the exact light or dark sidebar colour, removing
  the black transparency rectangle and its apparent shadow;
- the contact point lights only when the beak reaches it.

## Downloads

- Windows installer: `Corpus-Querier-Setup.exe`
- Linux Debian package: `corpus-querier_3.1.1_amd64.deb`
- Linux portable AppImage: `Corpus-Querier-x86_64.AppImage`
- macOS Apple Silicon: `Corpus-Querier-macOS-arm64.dmg`
- macOS Intel: `Corpus-Querier-macOS-x86_64.dmg`

The installers include all Python dependencies.
