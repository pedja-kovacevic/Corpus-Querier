# Corpus Querier 3.1.2

Corpus Querier 3.1.2 is a corrective release for long Russian National Corpus
runs and resumed spreadsheets.

## Corrections

- RNC responses with an HTTP-success status, a valid `queryStats` object and an
  explicitly empty `groups` list are now recorded as **0 hits**. The API omits
  `wordUsageCount` for some genuine zero-result queries and does not use
  consistent zero-valued pagination fields.
- Network failures, HTTP errors, explicit API error payloads and malformed
  responses remain errors; they are not converted into zeroes.
- Existing result spreadsheets can now be resumed safely. Numeric results are
  retained and skipped instead of being parsed as queries.
- A previous `ERROR` in an automatically generated workbook is reconstructed
  from the template in row 1 and the lexical item in column A, then queued
  again. This allows earlier false errors to be repaired.
- Curly quotation marks, guillemets, non-breaking spaces, invisible spacing and
  CSV-style doubled quotes are normalized before RNC query translation.
- The pecking bird now tilts through a clearer arc while its platform remains
  completely stationary.

## Verification

- The supplied 5,000-item RNC workbook was inspected: it contains 139 `ERROR`
  cells, no numeric zeroes, and failures concentrated in the most restrictive
  query column. This is consistent with zero-result responses being
  misclassified by the previous parser.
- Automated coverage includes explicit zeroes, omitted-count empty responses,
  malformed/error responses, resumed numeric cells, recoverable prior errors,
  typographic quote normalization, and the wider bird animation.

## Installers

- Windows: `Corpus-Querier-Setup.exe`
- Linux: `corpus-querier_3.1.2_amd64.deb`
- Linux portable: `Corpus-Querier-x86_64.AppImage`
- macOS Apple Silicon: `Corpus-Querier-macOS-arm64.dmg`
- macOS Intel: `Corpus-Querier-macOS-x86_64.dmg`
