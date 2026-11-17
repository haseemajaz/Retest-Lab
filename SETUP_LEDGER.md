# Setup ledger — what happened to each setup

A reference trace is a flat list of bars. The ledger groups it into setups so
a trace can be read setup by setup instead of bar by bar.

## What a setup is

A setup starts on a bar with an `armed_long` or `armed_short` event and ends
on the first later bar that stops, reaches target 4, or is cancelled — or it
is still open when the trace ends. A setup that never fills is still a setup;
arming is a model decision, filling is a later threshold event.

## Outcomes

| Outcome | Meaning |
| --- | --- |
| `all_targets` | Target 4 was reached. Targets 1–3 were reached on the way; the ledger lists them. |
| `stop` | The stop threshold was reached while active. Targets hit before the stop are listed. |
| `cancelled` | The setup was cancelled before it ended any other way. The `cancel_reason` names why: `expired`, `outside_session`, `day_rollover`, or `stop_before_fill`. |
| `open` | The trace ended before the setup ended. It has no end bar yet. |

## What the ledger reports per setup

Setup number, day, direction, armed bar, end bar, bars held, entry, stop,
targets 1–4, fill bar (blank if it never filled), targets hit, outcome,
cancel reason, and how many ambiguous bars fall inside the setup. A flagged
bar's outcome is a modelling convention, not an observed sequence — it is
counted on its setup so it is never silently folded into an outcome.

## CLI

```sh
python -m reference.engine sample_ledger.csv --output sample_ledger_trace.csv
python -m reference.ledger sample_ledger_trace.csv --output ledger.csv
```

Without `--output` the ledger CSV goes to stdout and a one-line summary
follows it. An existing output file is refused unless `--force` is given;
the output must never be the input trace. The audit report (`python -m
reference.audit_report`) includes the same ledger as its "Setup outcomes"
section.

## Example

`sample_ledger.csv` (29 bars) traces to three setups:

| Setup | Armed | End | Fill | Targets hit | Outcome |
| --- | --- | --- | --- | --- | --- |
| 1 | 20 | 22 | 21 | 1, 2, 3, 4 | all_targets |
| 2 | 28 | 31 | 29 | 1 | stop |
| 3 | 37 | 48 | — | — | cancelled / expired |

Summary: `3 setup(s): 1 reached all targets, 1 stopped, 1 cancelled
(expired: 1), 0 still open. Filled: 2 of 3. Ambiguous bars inside setups: 1.`

## What the ledger does not do

It calculates no win rate, return, or profitability, and it does not
establish Pine parity or execution. It counts modeled threshold events
only. A setup that reached all targets on one trace is not evidence it
will do so on another — and a flagged outcome must not be counted as a
win or a loss without finer data.
