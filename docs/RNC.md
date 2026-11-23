# Russian National Corpus provider — Corpus Querier 3.0

Corpus Querier RNC is an experimental desktop client for the official Russian
National Corpus API. It converts compact, CQL-like templates into native RNC
lexical–grammatical requests, runs them in batches, and saves the results to
Excel.

## Security

Paste your personal RNC API token into the masked field and use **Test
connection** before a batch run. The token is held in memory only: it is not
written to the workbook or source code. It may alternatively be supplied through
the `RNC_API_TOKEN` environment variable.

If a token has been posted publicly, revoke it and generate a replacement.

## Query syntax

The app supports these aliases:

| Compact attribute | Native RNC field |
|---|---|
| `lemma`, `lex` | `lex` |
| `word`, `form` | `form` |
| `tag`, `gramm` | `gramm` |
| `lemma_regex`, `lex_regexp` | Base64-encoded `lex_regexp` |
| `word_regex`, `form_regexp` | Base64-encoded `form_regexp` |
| `dist` | token distance range |

Examples:

```text
[lemma="море"]
[word="моря"]
[lemma=".*ение"]
[lemma="книга" & gramm="(S) & -(gen|gen2)"]
[lemma="синий"] [lemma="мяч" & dist="1:3"]
```

Important grammar formatting is applied automatically: spaces are retained
around `&`, while spaces around `|` are removed. A `tag` value must already be
a native RNC grammatical formula. The app does not translate tagsets from
Sketch Engine or another corpus.

Supported Boolean operations include grammatical AND, OR, and negation, plus OR
between alternatives of the same lexical attribute. Cross-attribute OR,
lexical negation, CQL repetition, and structural constraints are rejected rather
than guessed.

Full JSON requests exported by the RNC interface are also accepted.

## Batch generation

Words or lemmas can be typed directly or loaded from an Excel column. Templates
use `{LEMMA}` or `{WORD}`:

```text
[lemma="{LEMMA}"]
[lemma="{LEMMA}" & gramm="(S)"]
[lemma_regex=".*{LEMMA}"]
```

The query-builder row can generate these templates without requiring the user
to write the brackets manually.

## Subcorpus filters

The interface exposes creation-year range, author, author sex, primary category,
sphere, topic, text type, and genre. An advanced field/value pair accommodates
additional native RNC metadata attributes.

Subcorpus alternatives use a pipe with or without spaces in the interface; the
app emits the RNC form `value 1 | value 2`. This differs from grammar formulas,
where the app emits no spaces around `|`.

## Output modes

### Exact total frequency

The result cell contains `queryStats.wordUsageCount`. This is the exact total
reported by the API and preserves the original Corpus Querier output style.

A successful response containing an explicit count of zero is saved as numeric
`0`. The RNC may also omit `wordUsageCount` for an empty concordance; Corpus
Querier accepts that case as zero only when the response contains an empty
`groups` list plus an explicit zero-valued text, document or pagination signal.
Missing or malformed counts without that evidence remain `ERROR`, so server and
response failures are not silently converted into linguistic zeroes.

### Exact total + sampled forms

The **Results** sheet contains exact totals. Two additional long-format sheets
are created:

- **Sampled forms**: one form per row with its count in the returned concordance
  sample;
- **Concordance sample**: hit forms, context, document ID, and available title.

### Sampled forms only

Forms remain one per row in **Sampled forms**. The main results cell points to
that sheet.

Capitalization variants can be merged with Unicode case-folding, and a minimum
sample count can be selected. These settings apply only to returned concordance
samples—not to the exact total.

> The RNC concordance endpoint may contain hundreds of pages. A form count from
> the returned page is therefore a sample, not an exhaustive form-frequency
> distribution. The app labels it accordingly.

## Running from source

```bash
python -m pip install -r requirements-rnc.txt
python Corpus-Querier-RNC.py
```

Run the offline tests with:

```bash
python -m unittest -v
```

## Reliability behavior

- at least two request attempts per query;
- the highest valid exact total is retained;
- configurable delay and timeout;
- periodic Excel saving;
- stop-and-save;
- progress, elapsed time, and ETA;
- validation before the batch starts.
- explicit separation of confirmed zero results from malformed responses.

The API token is never embedded in an installer or repository.
