# Corpus Querier 3.0 — Release Candidate 1

Corpus Querier is a cross-platform desktop application for reproducible batch
corpus research. Version 3 adds the official Russian National Corpus public API
while preserving the complete CLARIN.SI workflow from version 2.

The opening screen asks the user to choose a provider:

- **CLARIN.SI** — Sketch Engine/Bonito CQL searches;
- **Russian National Corpus** — native RNC lexical–grammatical searches.

This is a release candidate intended for testing. Version 2.0 remains the
current stable release until the acceptance tests below pass.

## What version 3 contains

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

### CLARIN.SI provider

- any available CLARIN.SI corpus name;
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

### Russian National Corpus provider

- masked personal API-token input and connection testing;
- native lemma, surface-form, regular-expression and grammatical searches;
- Base64 encoding of RNC regex fields;
- Boolean grammatical formulas and word-distance ranges;
- creation date, author, author sex, category, sphere, topic, text type, genre
  and advanced metadata filters;
- exact total occurrence counts from `queryStats.wordUsageCount`;
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
| CLARIN total frequency | Exact API total |
| CLARIN form-frequency list | Complete frequency response |
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

## Release-candidate acceptance tests

Publication as 3.0 requires all of the following:

1. **Automated tests**
   - translator and response-parser tests pass;
   - CLARIN v2 regression tests pass;
   - spreadsheet cells accept totals and error markers;
   - all three packaging workflows complete.
2. **CLARIN smoke test**
   - one existing-query workbook;
   - one generated-template run;
   - total-frequency mode;
   - total plus forms/frequencies mode;
   - capitalization grouping and a threshold greater than one;
   - two visibly completed attempts.
3. **RNC smoke test**
   - token validation;
   - one literal lemma query;
   - one regex query;
   - one grammatical query;
   - one metadata/date-filtered query;
   - exact-total mode and exact-total-plus-sampled-forms mode;
   - two visibly completed attempts.
4. **Spreadsheet verification**
   - correct totals and query labels;
   - separate numeric cells for form frequencies;
   - RNC sample scope clearly recorded;
   - workbook opens without a repair warning;
   - stop-and-save preserves completed work.
5. **Installer verification**
   - Windows installer launches without Python installed;
   - Debian package or AppImage launches on Linux;
   - both macOS DMGs launch on their respective architectures, subject to the
     expected unsigned-app warning;
   - provider selection and one short query work in every tested package.

The same linguistic counts do not need to be repeated on every platform. One
full functional test per provider plus launch tests for the remaining packages
is sufficient once the shared source build has passed automated tests.

## Building packages

The GitHub Actions workflows can be run manually against the development branch.
They upload installable artifacts without publishing a release. Final packages
are attached to a release only when the approved `v3.0.0` tag is pushed.

## License and acknowledgment

Corpus Querier is released under the MIT License. CLARIN.SI and the Russian
National Corpus provide the corpus-querying infrastructure used by the app.
