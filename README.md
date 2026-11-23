# Corpus Querier 3.1

Corpus Querier is a cross-platform desktop application for reproducible batch
corpus research. Version 3.1 combines NoSketch Engine/CLARIN.SI, the official
Sketch Engine API, and the Russian National Corpus public API in one interface.

The opening screen asks the user to choose a provider:

- **NoSketch Engine** — CLARIN.SI-hosted Bonito CQL searches;
- **Sketch Engine** — authenticated official API searches, including the BNC;
- **Russian National Corpus** — native RNC lexical–grammatical searches.

## Download and install

Open the [latest GitHub release](https://github.com/pedja-kovacevic/Corpus-Querier-CLARIN/releases/latest)
and download the package for your system:

| Platform | Download |
|---|---|
| Windows | `Corpus-Querier-Setup.exe` |
| Linux (Debian/Ubuntu/MX Linux) | `corpus-querier_3.1.0_amd64.deb` |
| Linux portable | `Corpus-Querier-x86_64.AppImage` |
| macOS Apple Silicon | `Corpus-Querier-macOS-arm64.dmg` |
| macOS Intel | `Corpus-Querier-macOS-x86_64.dmg` |

The installers contain the application and its Python dependencies. End users
do not need Python, PowerShell, Visual Studio Code or a terminal.

## What version 3.1 contains

### Shared capabilities

- existing-query Excel spreadsheets;
- automatic query generation from typed items or an Excel column;
- reusable `{LEMMA}` and `{WORD}` templates;
- at least two complete attempts for every query;
- configurable request delay and timeout;
- progress, elapsed time and ETA;
- periodic saving and **Stop & save**;
- capitalization grouping and minimum-frequency thresholds where forms are
  available;
- Windows, Linux and macOS packaging.

Version 3.1 uses a shared visual identity on every platform: a stylized data
bird pecking a highlighted point from a corpus surface. The larger in-app bird
animates only while a query run is active, and the contact point lights briefly
at each peck.

### NoSketch Engine provider

- any available corpus name on the connected CLARIN.SI NoSketch Engine service;
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
   - CLARIN v2 regression tests pass;
   - spreadsheet cells accept totals and error markers;
   - all three packaging workflows complete.
2. **NoSketch Engine smoke test**
   - one existing-query workbook;
   - one generated-template run;
   - total-frequency mode;
   - total plus forms/frequencies mode;
   - capitalization grouping and a threshold greater than one;
   - two visibly completed attempts.
3. **Sketch Engine smoke test**
   - API-key validation;
   - one BNC exact-total query;
   - one generated-template run;
   - two visibly completed attempts.
4. **RNC smoke test**
   - token validation;
   - one literal lemma query;
   - one regex query;
   - one grammatical query;
   - one metadata/date-filtered query;
   - exact-total mode and exact-total-plus-sampled-forms mode;
   - one genuine zero-result query saved as `0`;
   - one deliberately malformed response retained as `ERROR`;
   - two visibly completed attempts.
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
packages are attached automatically when a release tag such as `v3.1.0` is
pushed.

## License and acknowledgment

Corpus Querier is released under the MIT License. CLARIN.SI, Sketch Engine and
the Russian National Corpus provide the corpus-querying infrastructure used by
the app.
