# Replay capture and comparison

This is a manual research aid, not an automated TradingView integration, a backtest, or proof of parity, execution or profitability. The sample observations are **synthetic**, not chart observations. The Pine script must first compile on a standard chart; see `TEST_PLAN.md` and `VALIDATION.md`.

## Record the setup

Copy this section for each run and fill it from the actual chart, leaving unknowns explicit. Do not overwrite prior evidence.

- Date/time and observer:
- Script version and exact source/commit; compile and runtime result:
- Symbol, exchange/feed, adjustments, chart type, timeframe, tick size:
- Chart timezone, indicator session timezone and session settings:
- Every indicator input (including defaults); matching Python JSON config and tick:
- Replay interval and warm-up history; index-to-chart timestamp mapping (include timezone/offset):
- Source of prepared prior high/low/ATR, EMA, VWAP, volume and session flags; include unavailable values:
- Files saved (chart screenshots, input CSV, config JSON, trace CSV, observations CSV), known limitations:
- Scenario/acceptance-matrix row and result: **not tested / observed match / difference / inconclusive**. Record the bar/time and explanation for differences; do not mark an unobserved event passed.

The Python trace starts idle and only accepts consecutive confirmed bars. Prepare OHLC and prior values from the same feed, timeframes, session and indicator settings, including enough history for matching state. The comparison cannot check whether these assumptions were met. Record errors and preserve mismatches rather than altering evidence to force a match.

## Preflight prepared bars

Before generating a trace, run `python -m reference.preflight your_bars.csv --config your_config.json` (omit `--config` to use defaults). It reads the CSV and config without changing either, validates inputs using the same Python model as the trace, and reports counts and up to five affected indexes per warning category. It flags omitted or blank `in_session` and `confirmed` values, which the trace treats as true; missing timestamps or timestamps without timezone offsets; bars with all prior-range/ATR inputs blank or prior ATR zero, where breakout detection is skipped; and missing EMA, VWAP or volume inputs when the relevant filter is enabled. A zero prior volume average is also flagged when its filter is enabled. Filter warnings apply only on bars with prepared prior range and positive ATR. Invalid rows, including unconfirmed bars, stop the check with an error.

### Consolidated audit report (v0.15.0)

Run `python -m reference.audit_report --bars sample_trace.csv --observations sample_observations.csv --required sample_required.csv --output audit.html` for a synthetic example. The generated HTML combines model preflight, a bounded event preview, recorded-cell comparison and input hashes. Omit observations to create a report that says comparison was **not run**. See `AUDIT_REPORT.md` for the full command, limits, exit codes, no-overwrite behavior and privacy cautions. Inputs are snapshotted sequentially; fingerprints do not authenticate them or fingerprint the executed code. This is not Pine or performance validation.

### Visual trace viewer (v0.14.0)

1. From the extracted folder run `python -m reference.engine sample_trace.csv --output trace.csv` (choose a new output path; existing files are protected). The sample is synthetic.
2. Open `TRACE_VIEWER.html` in a modern browser, select the generated output CSV, or choose **Load synthetic example**. Use the event filter and Previous/Next controls to inspect rows. A failed import leaves the existing view unchanged.
3. The viewer accepts a UTF-8 engine trace with the exact output headers, up to 2 MiB, 5,000 rows and 1,024 characters per cell. It requires consecutive safe-integer indexes. It performs structural checks only, not validation of state transitions, provenance or correctness. Data is read locally and is not persisted by the viewer.
4. Counts summarize event strings in the file. A target count is the number of target events, not the number of trades. Never interpret counts as real fills, returns or performance. Follow the independent observation comparison below; the viewer neither compares observations nor runs Pine.

Preflight now also warns if a CSV decimal visibly changes when parsed as a Python float, and if OHLC/prior range price magnitudes reach 2^53 configured ticks. These warnings are incomplete and can miss binary representation or later arithmetic errors; 0.1 is a simple example. They do not establish correct Pine arithmetic, feed accuracy or tick rules. `--strict` treats these warnings like other preflight warnings.

### Additional data-quality checks (v0.13.0)

Unknown headers are listed as ignored, exposing possible misspellings. Intentional extra metadata also warns; trace behavior is unchanged. Preflight compares nearest offset-aware timestamps across blank or naive gaps, but cannot infer missing values or cadence.

Optional: `python -m reference.preflight your_bars.csv --config your_config.json --check-tick --strict`. Set the constant tick deliberately; without a config it defaults to 0.01. Exact decimal OHLC values are checked; ATR, EMA and VWAP are not. Inputs with over 100 decimal digits or absolute exponent above 100 are reported unchecked. Adjusted data and variable-tick markets may legitimately be off-grid. No input is changed. Strict mode reports any warning as status 1, including expected warm-up or intentional extra columns.

Open `REPLAY_WORKSPACE.html` for a visual workflow guide. It does not execute checks or connect to a chart.

Preflight exit codes are 0 for valid inputs (including warnings), 1 only when `--strict` is used and warnings exist, and 2 for invalid inputs or unreadable files. For example, `python -m reference.preflight sample_trace.csv --strict` reports expected synthetic gaps and exits 1. Review each warning in context rather than inventing data to clear it; blank prior values can be intentional during warm-up or when detection is deliberately not evaluated.

Adjacent offset-aware timestamps are also checked for repeated instants or backwards ordering. Offsets are compared as instants, and a blank or naive timestamp breaks the comparison chain. This is only a warning; it does not verify expected cadence, session or timestamp-to-bar mapping. The trace accepts timestamp order as supplied.

CSV rows must include the same number of fields as their header (use explicit empty cells for blanks); duplicate JSON config keys are rejected.

This is not an independent test of the Python engine. It cannot verify source/feed, data accuracy, actual session membership, timezone mapping, enough warm-up, Pine parity, alerts, execution or profitability. A clean result does not prove any of these.

## Compare observations

1. Choose a new output file; the trace refuses to replace existing files unless you explicitly add `--force`. Input/config aliases and output symlinks are always refused. No-clobber creation requires hard-link support in the output directory. The Python reference rejects ticks requiring more than ten decimal places; this does not prove rounding parity with Pine. Generate a trace: `python -m reference.engine your_bars.csv --config your_config.json --output trace.csv`. Omit `--config` when using defaults. Do not overwrite evidence. Trace inputs and columns are described in `README.md`.
2. Create an observation CSV with the **exact** headers `index,field,value`. Enter one independently observed value per row, using the same consecutive index as the trace. Use the precise field names and values below. Only record fields that can actually be observed on the chart, or otherwise independently established; omit unknowns. Do not copy the reference output as an observation.
3. Run `python -m reference.compare_trace trace.csv observations.csv`. The command reads both files and prints a summary and differences; it does not write or change either file. The output shows how many trace bars contain observations and per-field counts; presence is not a claim that the observation is correct. Exit status: 0 means all *recorded* cells matched and, if supplied, no checklist cells are missing; 1 means differences or missing required observations; 2 means input error. A result with no differences is not proof of overall parity.

Allowed fields match the trace: `timestamp`, `day`, `state_before`, `state`, `events`, `cancel_reason`, `direction`, `entry`, `stop`, `t1`, `t2`, `t3`, `t4`, `fills_today`, `targets_hit`. Values for state are `idle`, `armed`, `active`; direction is `1` or `-1`. Event lists use exact reference labels such as `armed_long`, `armed_short`, `modeled_fill`, `stop`, `cancelled`, `target_1` … `target_4`, separated by `|` in the same order. Target hit lists use e.g. `1|2`. Cancellation reasons use `day_rollover`, `outside_session`, `expired`, `stop_before_fill`. Only record an empty `value` if an empty value was positively observed; omit unknowns. Numeric fields are compared as exact decimal values (`100`, `100.0` match); there is no tolerance or automatic tick rounding. Other fields are case- and order-sensitive, with outer whitespace ignored. Timestamps must match as text, including offset; do not infer equivalent timestamps. An unknown or duplicate field/index pair and an index absent from the trace are errors.

Some internal state or cancel reasons may not be visible on the chart: omit them unless independently observed. Do not infer a modeled fill from broker execution or use absence of an alert as proof of an event. Realtime alert checks are separate from Bar Replay.

## Optional planned-observation checklist

To catch missing planned observations, create a separate CSV with the exact headers `index,field`. List each specific trace index and field you intend to observe, one pair per row. Plan only observations that can genuinely be made; never invent values to satisfy the checklist. Indices must occur in the trace, fields must use the allowed names above, and duplicate pairs, malformed rows and an empty checklist are errors.

Run `python -m reference.compare_trace trace.csv observations.csv --required checklist.csv`. The report counts planned cells that have an observation and lists missing pairs (at most 30 shown, with the remainder counted). Missing cells make the exit status 1, even when all recorded values match. All observations are still compared, including any not in the checklist. With a checklist, an observations file containing only its header reports all planned cells missing; without a checklist, an empty observations file remains an error. Blank values count as present only because they explicitly represent an observed empty value; omit unknown values. The tool reads all files without changing them.

`sample_required.csv` is a synthetic example matching the long sample. Try `python -m reference.compare_trace sample_trace_output.csv sample_observations.csv --required sample_required.csv` after producing the sample trace below. Checklist coverage cannot verify that values are truthful, settings match, or that the plan covers all relevant behavior. It cannot substitute for a full test or prove parity.

## Synthetic example

`sample_observations.csv` is hand-written for the made-up bars in `sample_trace.csv`. It illustrates the file format only, not an actual chart test:

```sh
python -m reference.engine sample_trace.csv --output sample_trace_output.csv
python -m reference.compare_trace sample_trace_output.csv sample_observations.csv
```

Use new file names for real captures and keep their provenance. A match merely confirms that these recorded sample cells agree with this reference model.

A second synthetic short case is provided as `sample_short_trace.csv` and `sample_short_observations.csv`. Repeat the commands above with those names and a different output file. Both examples share the model's assumptions and are not independent Pine validation.

## Offline capture worksheet (v0.16.0)

Open `CAPTURE_WORKSHEET.html` to record planned index/field cells without loading the model trace. Export a checklist and observations without changing the worksheet between downloads. A checked blank is a recorded blank; unchecked rows are missing. It does not verify the chart or model. No automatic persistence is provided; see `CAPTURE_WORKSHEET.md` for privacy, spreadsheet formula warnings and limits.

## Capture backup (v0.17.0)

The worksheet can explicitly download and restore a local JSON draft, including incomplete and unchecked values. A malformed backup leaves the current worksheet unchanged; replacing an existing worksheet requires confirmation. Backups are not encrypted or automatically saved. See `CAPTURE_WORKSHEET.md` for restore limits and CSV-export rules.

## Arithmetic guard (v0.18.0)

The Python reference rejects a non-finite result from a checked, evaluated model operation and reports the CSV row. Trace, preflight and audit share this path; exit 2 is an error, not a warning or successful check. Correct only verified input mistakes. The check does not detect every underflow or finite precision error. See `NUMERIC_SAFETY.html` and `TECHNICAL_REVIEW.md`.


For a separate demonstration of decimal versus floating tick-index decisions, open `ROUNDING_INSPECTOR.html`; see `ROUNDING_INSPECTOR.md`. It does not validate the trace or Pine.


## Optional cadence check

Preflight and audit accept `--expected-seconds N` for a fixed expected positive interval, 1 to 31,536,000 whole seconds. For example, `python -m reference.preflight sample_cadence.csv --expected-seconds 300 --strict` flags the synthetic sample's long and short intervals and intentionally returns 1. The later bar index is shown for each affected pair. Only adjacent pairs with explicit timezone offsets are checked, comparing absolute instants; missing or naive timestamps produce unchecked-pair warnings. A single-bar file has no interval to check. Equal and backward timestamps remain separate ordering warnings. This option is off by default and changes neither inputs nor model behavior. See `CADENCE_GUIDE.html`.

The tool has no exchange calendar, does not determine whether gaps are missing bars, and does not verify data origin, timezone conventions, bar open versus close times, session boundaries, Pine parity or trading performance. Closures, breaks, DST conventions and variable-duration bars can yield legitimate differences; investigate original data rather than inventing rows.
