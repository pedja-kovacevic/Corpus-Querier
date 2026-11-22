# Corpus Querier 3.0.0

Corpus Querier 3 combines two corpus providers in one cross-platform desktop
application while keeping their query languages and result scopes explicit.

## Highlights

- **CLARIN.SI provider:** CQL batch queries, exact total frequencies, exact
  form lists and form frequencies.
- **Russian National Corpus provider:** official RNC API access, exact total
  frequencies, concordance samples, sampled forms and subcorpus metadata
  filters.
- **Spreadsheet automation:** existing query sheets or automatic query
  generation from `{LEMMA}` and `{WORD}` templates.
- **Research controls:** mandatory repeated attempts, configurable delays and
  timeouts, capitalization grouping, form-frequency thresholds, progress,
  ETA, periodic saving and Stop & save.
- **Shared visual identity:** the new data-bird icon is used by the app,
  shortcuts and installers on Windows, Linux and macOS.

RNC total frequencies are exact. RNC form and concordance worksheets describe
the returned API sample and are deliberately not presented as exhaustive form
distributions.

## Downloads

- **Windows:** `Corpus-Querier-Setup.exe`
- **Linux (Debian/Ubuntu/MX Linux):** `corpus-querier_3.0.0_amd64.deb`
- **Linux portable:** `Corpus-Querier-x86_64.AppImage`
- **macOS Apple Silicon:** `Corpus-Querier-macOS-arm64.dmg`
- **macOS Intel:** `Corpus-Querier-macOS-x86_64.dmg`

The packaged applications include their Python dependencies. Python and a
development environment are not required.

**Full changelog:** https://github.com/pedja-kovacevic/Corpus-Querier-CLARIN/compare/v2.0.0...v3.0.0
