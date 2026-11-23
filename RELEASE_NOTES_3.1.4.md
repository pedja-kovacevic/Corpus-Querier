# Corpus Querier 3.1.4

Version 3.1.4 gives Corpus Querier a provider-neutral identity and completes
the transition to the simplified **Corpus-Querier** repository name.

## Changes

- renames the integrated provider throughout the interface to **NoSketch Engine**;
- removes CLARIN branding from buttons, window titles, logs, package metadata,
  internal module names and current documentation;
- retains `www.clarin.si` only as factual endpoint information for the public
  Bonito server currently used by the NoSketch Engine module;
- adds a clear statement that Corpus Querier is independently developed and
  is not affiliated with or endorsed by any corpus provider;
- renames the active repository to `Corpus-Querier` and preserves the original
  prototype as `Corpus-Querier-Legacy`;
- preserves the Linux icon fixes, RNC zero-result handling, recovery of
  unfinished spreadsheets, and mandatory repeated query attempts from 3.1.3.

## Providers

- NoSketch Engine / Bonito
- authenticated Sketch Engine API
- Russian National Corpus public API

Installers are produced for Windows, Linux, macOS Intel and macOS Apple Silicon.
