# Corpus Querier 3.3

Corpus Querier is an independent, cross-platform desktop application for
reproducible batch corpus research. Version 3.3 combines NoSketch Engine,
the official Sketch Engine API, and the Russian National Corpus public API in
one interface.

The opening screen asks the user to choose a provider:

- **NoSketch Engine** — public Bonito CQL searches;
- **Sketch Engine** — authenticated official API searches, including the BNC;
- **Russian National Corpus** — native RNC lexical–grammatical searches.

## Download and install

Open the [latest GitHub release](https://github.com/pedja-kovacevic/Corpus-Querier/releases/latest)
and download the package for your system:

| Platform | Download |
|---|---|
| Windows | `Corpus-Querier-Setup.exe` |
| Linux (Debian/Ubuntu/MX Linux) | `corpus-querier_3.3.0_amd64.deb` |
| Linux portable | `Corpus-Querier-x86_64.AppImage` |
| macOS Apple Silicon | `Corpus-Querier-macOS-arm64.dmg` |
| macOS Intel | `Corpus-Querier-macOS-x86_64.dmg` |

The installers contain the application and its Python dependencies. End users
do not need Python, PowerShell, Visual Studio Code or a terminal.

## What version 3.3 contains

### Shared capabilities

- existing-query Excel spreadsheets;
- automatic query generation from typed items or an Excel column;
- reusable `{LEMMA}` and `{WORD}` templates;
- configurable attempts per query: choose `1` for speed or `2` and above for
  repeated verification;
- configurable request delay and timeout;
- progress, elapsed time and ETA;
- **Pause / Resume** between network requests, without losing the current run;
- periodic saving and **Stop & save**, including while paused;
- configurable rolling request limits under **Advanced options**, prefilled
  with `100/minute`, `900/hour` and `2,000/day`;
- a warning when only 10 requests remain in any rolling limit window and an
  automatic pause when only three remain, with the next safe check shown in
  the interface;
- persistent request accounting across app restarts so reopening Corpus
  Querier does not silently reset the daily counter;
- a 24-hour safety pause after 10 consecutive failed NoSketch Engine or Sketch
  Engine queries; the user may resume earlier or stop and save;
- capitalization grouping and minimum-frequency thresholds where forms are
  available;
- Windows, Linux and macOS packaging.

Version 3.3 uses a shared visual identity on every platform: a stylized data
bird pecking a highlighted point from a corpus surface. The larger in-app bird
animates only while a query run is active, and the contact point lights briefly
at each peck.

### NoSketch Engine provider

- any available corpus name on the connected NoSketch Engine service;
- standard CQL input;
- exact total query frequency;
- exact form lists and form frequencies returned by the Bonito frequency
  endpoint;
- four output modes inherited from Corpus Querier 2.0;
- backward-compatible total-frequency spreadsheets.

Example:

```cql
[lemma="čitati"]
[lemma="čitati" & tag="Vmr3s"]
```

### Sketch Engine provider

- a masked personal API-key field and connection test;
- access to corpora enabled for the user's Sketch Engine account;
- the British National Corpus as the default test corpus;
- standard CQL input and template generation;
- exact total frequencies and available form-frequency output;
- the same retry, progress, periodic-save and spreadsheet workflows as the
  NoSketch Engine module.

The default Sketch Engine request limits follow its published
[Fair Use Policy](https://www.sketchengine.eu/fair-use-policy/): 100 requests
in any rolling 60 seconds, 900 in any rolling 60 minutes and 2,000 in any
rolling 24 hours. The app counts actual HTTP requests, so two attempts for one
query consume two requests. Limits can be edited under Advanced options when
an account has a different quota.

CLARIN.SI does not publish an equivalent numeric quota for its public NoSketch
Engine service. The NoSketch module therefore starts with the same editable
defaults; they are a client-side safety profile, not a claim about that
server's contractual limit.

The persistent counter covers requests sent by Corpus Querier itself. Requests
made simultaneously in a provider's web interface or by another API client
cannot be observed locally and therefore are not included.

Example:

```cql
[lemma="travel"]
[lemma="travel" & tag="V.*"]
```

### Russian National Corpus provider

- masked personal API-token input and connection testing;
- native lemma, surface-form, regular-expression and grammatical searches;
- Base64 encoding of RNC regex fields;
- Boolean grammatical formulas and word-distance ranges;
- creation date, author, author sex, category, sphere, topic, text type, genre
  and advanced metadata filters;
- exact total occurrence counts from `queryStats.wordUsageCount`;
- confirmed zero-result responses are written as numeric `0`, while malformed,
  incomplete and HTTP-error responses remain `ERROR`;
- manual Pause / Resume is available, but the 10-error automatic cooldown is
  deliberately disabled for RNC while zero-result handling remains under
  provider-specific validation;
- sampled forms and concordance contexts in separate long-format worksheets.

Example:

```text
[lemma="море"]
[word="моря"]
[lemma=".*ение"]
[lemma="книга" & gramm="(S) & -(gen|gen2)"]
[lemma="синий"] [lemma="мяч" & dist="1:3"]
```

RNC `tag`/`gramm` values must already be native RNC formulas. Corpus Querier
does not silently translate another corpus's tagset.

## Exact results versus samples

The interface deliberately distinguishes result scope:

| Provider/result | Scope |
|---|---|
| NoSketch Engine total frequency | Exact API total |
| NoSketch Engine form-frequency list | Complete frequency response |
| Sketch Engine total frequency | Exact API total |
| Sketch Engine form-frequency list | Complete frequency response when available |
| RNC total frequency | Exact API total |
| RNC forms and contexts | Returned concordance sample |

An RNC concordance can contain hundreds of pages. The app never labels the
forms seen on one returned page as an exhaustive form-frequency distribution.

## RNC token security

The token is held in memory only. It is not written to source code, settings or
Excel output. Never commit a personal token to GitHub. Revoke any token that has
been posted or shared publicly.

## Source installation

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python Corpus-Querier.py
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

## Release validation

The release is checked with the following automated and manual tests:

1. **Automated tests**
   - translator and response-parser tests pass;
   - NoSketch Engine regression tests pass;
   - spreadsheet cells accept totals and error markers;
   - all three packaging workflows complete.
2. **NoSketch Engine smoke test**
   - one existing-query workbook;
   - one generated-template run;
   - total-frequency mode;
   - total plus forms/frequencies mode;
   - capitalization grouping and a threshold greater than one;
   - both one-attempt and two-attempt runs;
   - pause, resume and stop-while-paused behaviour;
   - rolling-limit warnings and automatic quota pauses.
3. **Sketch Engine smoke test**
   - API-key validation;
   - one BNC exact-total query;
   - one generated-template run;
   - both one-attempt and two-attempt runs;
   - automatic safety pause after 10 simulated consecutive failures;
   - persistent minute/hour/day request accounting and exact resume time.
4. **RNC smoke test**
   - token validation;
   - one literal lemma query;
   - one regex query;
   - one grammatical query;
   - one metadata/date-filtered query;
   - exact-total mode and exact-total-plus-sampled-forms mode;
   - one genuine zero-result query saved as `0`;
   - one deliberately malformed response retained as `ERROR`;
   - both one-attempt and two-attempt runs;
   - manual pause and resume, without the automatic 10-error cooldown.
5. **Spreadsheet verification**
   - correct totals and query labels;
   - separate numeric cells for form frequencies;
   - RNC sample scope clearly recorded;
   - workbook opens without a repair warning;
   - stop-and-save preserves completed work.
6. **Installer verification**
   - Windows installer launches without Python installed;
   - Debian package or AppImage launches on Linux;
   - both macOS DMGs launch on their respective architectures, subject to the
     expected unsigned-app warning;
   - provider selection and one short query work in every tested package.

The same linguistic counts do not need to be repeated on every platform. One
full functional test per provider plus launch tests for the remaining packages
is sufficient once the shared source build has passed automated tests.

## Building packages

The GitHub Actions workflows can be run manually against a development branch.
They upload installable artifacts without publishing a release. Versioned
packages are attached automatically when a release tag such as `v3.3.0` is
pushed.

## Service independence and acknowledgment

Corpus Querier is released under the MIT License. It is independently developed
and is not affiliated with or endorsed by any corpus provider. The NoSketch
Engine module currently connects to a Bonito server at `www.clarin.si`; that
domain is retained only as factual technical endpoint information. Sketch
Engine and the Russian National Corpus provide their respective query APIs.
