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

## Compare observations

1. Generate a trace: `python -m reference.engine your_bars.csv --config your_config.json --output trace.csv`. Omit `--config` when using defaults. Do not overwrite evidence. Trace inputs and columns are described in `README.md`.
2. Create an observation CSV with the **exact** headers `index,field,value`. Enter one independently observed value per row, using the same consecutive index as the trace. Use the precise field names and values below. Only record fields that can actually be observed on the chart, or otherwise independently established; omit unknowns. Do not copy the reference output as an observation.
3. Run `python -m reference.compare_trace trace.csv observations.csv`. The command reads both files and prints a summary and differences; it does not write or change either file. Exit status: 0 means all *recorded* cells matched, 1 means differences, 2 means input error. A result with no differences does not check missing bars or fields and is not proof of overall parity.

Allowed fields match the trace: `timestamp`, `day`, `state_before`, `state`, `events`, `cancel_reason`, `direction`, `entry`, `stop`, `t1`, `t2`, `t3`, `t4`, `fills_today`, `targets_hit`. Values for state are `idle`, `armed`, `active`; direction is `1` or `-1`. Event lists use exact reference labels such as `armed_long`, `armed_short`, `modeled_fill`, `stop`, `cancelled`, `target_1` … `target_4`, separated by `|` in the same order. Target hit lists use e.g. `1|2`. Cancellation reasons use `day_rollover`, `outside_session`, `expired`, `stop_before_fill`. Only record an empty `value` if an empty value was positively observed; omit unknowns. Numeric fields are compared as exact decimal values (`100`, `100.0` match); there is no tolerance or automatic tick rounding. Other fields are case- and order-sensitive, with outer whitespace ignored. Timestamps must match as text, including offset; do not infer equivalent timestamps. An unknown or duplicate field/index pair and an index absent from the trace are errors.

Some internal state or cancel reasons may not be visible on the chart: omit them unless independently observed. Do not infer a modeled fill from broker execution or use absence of an alert as proof of an event. Realtime alert checks are separate from Bar Replay.

## Synthetic example

`sample_observations.csv` is hand-written for the made-up bars in `sample_trace.csv`. It illustrates the file format only, not an actual chart test:

```sh
python -m reference.engine sample_trace.csv --output sample_trace_output.csv
python -m reference.compare_trace sample_trace_output.csv sample_observations.csv
```

Use new file names for real captures and keep their provenance. A match merely confirms that these recorded sample cells agree with this reference model.

A second synthetic short case is provided as `sample_short_trace.csv` and `sample_short_observations.csv`. Repeat the commands above with those names and a different output file. Both examples share the model's assumptions and are not independent Pine validation.
