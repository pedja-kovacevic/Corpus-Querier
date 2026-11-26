# Corpus Querier 3.3.0

Version 3.3 adds proactive rolling rate-limit protection to the NoSketch
Engine and Sketch Engine modules.

## Changes

- adds editable request-limit defaults under **Advanced options**:
  `100/minute`, `900/hour` and `2,000/day`;
- counts actual outbound HTTP requests rather than spreadsheet rows, so every
  configured query attempt is included;
- warns when only 10 requests remain in a rolling minute, hour or day window;
- pauses automatically before a request when only three requests remain;
- displays the exact local date and time of the next safe quota check;
- recalculates all rolling windows before resuming;
- prevents an early manual Resume from bypassing the three-request reserve;
- keeps **Stop & save** available during a rate-limit pause;
- persists the app's request timestamps across restarts so the daily counter
  cannot be reset accidentally by closing and reopening Corpus Querier;
- retains the separate 24-hour pause after 10 consecutive failed NoSketch or
  Sketch Engine queries;
- leaves the RNC module unchanged because it uses different provider-specific
  response and throttling behaviour.

The Sketch Engine defaults follow its published Fair Use Policy. CLARIN.SI
does not publish an equivalent numeric quota for the public NoSketch endpoint,
so those values are presented there as adjustable client-side safety defaults.

## Providers

- NoSketch Engine / Bonito
- authenticated Sketch Engine API
- Russian National Corpus public API

Installers are produced for Windows, Linux, macOS Intel and macOS Apple Silicon.
