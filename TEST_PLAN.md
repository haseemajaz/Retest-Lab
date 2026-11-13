# Retest Lab — TradingView acceptance and feature plan

Status: pending. This is a test protocol, not an assertion that v0.3 has compiled, matched the reference, or produced profitable trades. The v0.11.0 package contains the unchanged v0.3 Pine script. See [VALIDATION.md](VALIDATION.md) for completed checks.

## Prerequisites and safety
- Use a standard time-based candlestick chart, not Heikin Ashi or other synthetic bars. Record the ticker and exchange/feed, timeframe, tick size, chart session, chart timezone, the indicator's session timezone and every non-default input. Different feeds or adjustment settings can produce different bars and volume.
- Add the exact `retest_lab.pine` from this repository after making an indicator slot available. Record the compile result and any runtime errors. If saving requires freeing a script slot, back up existing work first; do not delete another script without its owner's permission. An unsaved script can disappear.
- Begin with Bar Replay and paper observation. Do not place real trades, connect a broker, create order-routing webhooks, or infer prop-firm compliance. Bar Replay does not test realtime alerts.

## Chart comparison protocol
1. Use defaults first. Record date/time, OHLC, prior range, prior ATR, direction, entry, stop and target levels at the arming bar; record all subsequent bars until the setup ends. Document price tick rounding. These inputs must come from the same chart and settings; the Python trace does not calculate indicators.
2. Include enough preceding history to reproduce the indicator state; the trace starts idle. Use consecutive absolute bar indexes, the indicator's local calendar day, prepared previous-range/ATR values, and matching `in_session` flags. Include EMA, VWAP and volume values when those filters are enabled. The CSV format and `sample_trace.csv` are documented in README.
3. Run `python -m reference.engine your_bars.csv --output trace.csv` with matching Config overrides and tick size, then compare bar by bar. A match is one example, not comprehensive or independent proof. If values differ, save the input CSV, inputs, feed, script version, expected/observed event and bar time; don't silently adjust the dataset.
4. Repeat on at least one long and one short setup, at least two symbols and timeframes, and with each filter tested alone and in combination. Record missing/unavailable volume or VWAP explicitly; don't assume a feed supplies reliable volume.

## Acceptance matrix

| Case | Expected model behavior to check | Result |
|---|---|---|
| Breakout and setup | Confirmed close strictly crosses the prior boundary; body/edge and risk geometry pass. Levels remain frozen while pending/active. | Not tested |
| Distance threshold | When enabled, the breakout distance meets the selected prior-ATR multiple; strictly crossing boundary remains required even at zero. | Not tested |
| Entry touch and gap | Only a later bar that spans entry can model a fill; a bar entirely beyond entry cannot. | Not tested |
| Close confirmation | When enabled, long close ≥ entry / short close ≤ entry is required on the entry-spanning bar. It does not guarantee a fill at that price. | Not tested |
| Pending stop and entry | Pending stop breach cancels before modeled entry, even if the bar spans both. | Not tested |
| Fill bar target | No target is recorded on the modeled-fill bar, even if its range crosses a target. | Not tested |
| Subsequent stop and target | If both thresholds are crossed on a later bar, stop takes priority. | Not tested |
| Later multiple targets | Crossed targets are recorded once; reaching T4 ends the model. | Not tested |
| Expiry | A touch is eligible through the configured subsequent-bar limit; the next bar cancels before filling. | Not tested |
| Day/session | Pending cancellation priority is day rollover, outside session, expiry, then stop. Active state continues across session/day changes. | Not tested |
| Cooldown and daily cap | No re-arm on the termination bar; the configured number of full bars is blocked. Daily cap counts modeled fills, not broker orders. | Not tested |
| Filters | EMA/VWAP comparisons are strict. Missing filter data rejects when required; relative-volume prior average must be positive. All enabled filters must pass. | Not tested |
| Display switches | Markers, levels, background, EMA/VWAP plots and dashboard can be hidden without changing model events. | Not tested |

## Realtime alert test (notification only)
After successful chart compilation and saving, create a temporary named condition and a separate `Any alert() function call` alert if the plan allows it. Do not attach a webhook. Observe actual realtime bar closes and compare the named event, JSON `schema` and cancellation reason to the chart. Delete only the temporary test alerts afterward. If no event occurs while observing, record **not observed**, not passed. TradingView alerts are snapshots; recreate after source/input changes. No alert is a broker execution.

## Reference examples, not chart results
The following were evaluated against the Python reference using default settings and tick 0.01; these are made-up bars and are not TradingView tests. CSV trace inputs are manually prepared. It is not possible to assume an actual market chart contains the same bars.

- **Long:** breakout bar O=99.5 H=102 L=99 C=101.8, prior high=100, prior low=95, prior ATR=2 → armed long at 100, stop 98.8, targets 100.72 / 101.20 / 101.80 / 102.40. Next bar O=100.4 H=100.5 L=100 C=100.2 → modeled fill. A subsequent bar O=101 H=102.5 L=97 C=101 → stop only, not targets.
- **Short:** breakout bar O=100.5 H=101 L=98 C=98.2, prior high=105, prior low=100, prior ATR=2 → armed short at 100, stop 101.2, targets 99.28 / 98.80 / 98.20 / 97.60. Next bar O=99.5 H=100 L=99 C=99.3 → modeled fill. A subsequent bar O=99 H=100 L=97 C=98 → target 1–4 and idle.

## Capture aid available
`REPLAY_CAPTURE.md` provides a guided evidence template and a read-only preflight command for prepared trace inputs. `python -m reference.compare_trace` compares manually recorded cells with the Python trace and flags differences. It reports observation coverage and can flag missing planned cells via an optional user-defined checklist. It does not observe a chart or validate unrecorded values; its synthetic examples are not Pine tests.

## Candidate future improvements — not implemented
1. **First:** complete compilation, alert checks and recorded replay cases above; repair any differences before adding decision logic.
2. **Better diagnostics:** a compact on-chart explanation of which enabled filter rejected a breakout, subject to Pine execution and display limits.
3. **Session visibility:** optional display of configured session windows and reset boundaries, with clear timezone labels.
4. **Comparison support:** additional independently checked edge-case fixtures. The guided capture format and selected-cell comparison are available, but Python traces and synthetic examples are not independent validation.

These are ideas, not tested features. No requested future feature implies a win-rate improvement or trade recommendation.
