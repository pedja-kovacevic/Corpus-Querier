# Corpus Querier 3.2.0

Version 3.2 adds direct run control for long corpus jobs and makes repeated
verification optional.

## Changes

- adds a **Pause / Resume** button to NoSketch Engine, Sketch Engine and RNC;
- finishes an active HTTP request before pausing and starts no new request
  until the run is resumed;
- keeps **Stop & save** available during both manual and automatic pauses;
- changes **Attempts/query** from a mandatory minimum of two to any positive
  integer, with two retained as the default;
- adds a 24-hour safety pause after 10 consecutive failed queries in NoSketch
  Engine and Sketch Engine;
- allows the user to interrupt that automatic pause with Resume or Stop & save;
- resets the consecutive-failure counter after every successful query;
- treats zero hits as a successful result, not a failure;
- deliberately excludes RNC from the automatic 10-error cooldown while keeping
  manual Pause / Resume and configurable attempts available there;
- adds automated pause, stop, cooldown-interruption and single-attempt tests.

## Providers

- NoSketch Engine / Bonito
- authenticated Sketch Engine API
- Russian National Corpus public API

Installers are produced for Windows, Linux, macOS Intel and macOS Apple Silicon.
