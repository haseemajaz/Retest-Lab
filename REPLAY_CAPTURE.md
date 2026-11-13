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

Preflight exit codes are 0 for valid inputs (including warnings), 1 only when `--strict` is used and warnings exist, and 2 for invalid inputs or unreadable files. For example, `python -m reference.preflight sample_trace.csv --strict` reports expected synthetic gaps and exits 1. Review each warning in context rather than inventing data to clear it; blank prior values can be intentional during warm-up or when detection is deliberately not evaluated.

This is not an independent test of the Python engine. It cannot verify source/feed, data accuracy, actual session membership, timezone mapping, enough warm-up, Pine parity, alerts, execution or profitability. A clean result does not prove any of these.

## Compare observations

1. Generate a trace: `python -m reference.engine your_bars.csv --config your_config.json --output trace.csv`. Omit `--config` when using defaults. Do not overwrite evidence. Trace inputs and columns are described in `README.md`.
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
