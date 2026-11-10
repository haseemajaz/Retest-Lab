# Validation record — v0.4.0 package / v0.3 Pine indicator

## Completed
- 2026-11-10: calculator: 22 JavaScript unit tests passed (`node --test tests/test_geometry.cjs`) covering long/short examples, tick alignment, half-tick rounding direction, target collapse, number bounds and invalid inputs. 79 Python reference/CLI tests also passed.
- 2026-11-10: locally tested the self-contained calculator in a headless browser: long sample, short case, CSV download contents, input invalidation, error handling, mobile width and no external network requests. Manual layout review included desktop/mobile and light/dark. These are calculator checks, not market data, performance or Pine parity tests.
- v0.4.0 adds the standalone calculator and changes no Pine logic. The indicator has not been newly compiled or replay-tested.
- 2026-11-08: 79 Python unit/CLI tests pass on synthetic inputs; sample CSV CLI output was inspected for an armed long, modeled fill and four later target events. Malformed non-finite input was rejected. The trace and tests use the same reference model, and this is not Pine/Python parity or a trading-performance test.
- 2026-11-08: the account's existing chart still showed Breakout Probability and EMA using the two Basic indicator slots. They were not removed; v0.3 could not be added without an available slot. The v0.3.1 package leaves the Pine indicator unchanged.
- 2026-11-07: 52 Python synthetic unit tests pass (`python -m unittest discover -s tests -v`); `test_results.txt` records the output. The Python reference takes prepared indicators rather than obtaining market data. These tests do not compile Pine, independently validate parity, or measure trading returns.
- v0.2 compiled and displayed on an AAPL daily chart and a five-bar Bar Replay smoke test showed no visible runtime error. That was v0.2, NOT this release.
- A v0.3 TradingView Add to chart attempt was blocked before a successful chart test: the Basic plan chart already contained the two permitted indicators. Create new layout also reported the one-layout plan limit. Existing chart indicators were not removed. Earlier saving v0.2 was blocked by the one-saved-script limit. v0.3 is not confirmed saved.
- The video transcript was read on 2026-11-07; the video player did not load. Auto captions can mis-transcribe technical terms, and no visuals or trading records were independently verified.

## Still required before reliance
- Compile and add the unchanged v0.3 Pine script on a standard candlestick chart once a slot is available, then replay long/short, minimum-distance and close-confirmation boundaries, filters including missing volume/VWAP, stop/target ties, expiry, day/session changes, cooldown/cap and ticks. Compare to Python with matched inputs and recorded bars.
- Test real-time named and v3 JSON alerts separately, without broker routing; alerts do not fire on historical/replay bars. Check snapshots and cancel_reason.
- Cross-market/timeframe paper observation, then independently designed out-of-sample research with commissions, spread, slippage and realistic order execution. No win-rate claim is validated. Never interpret indicator results as compliance with a prop firm's rules.
- Fill-bar targets deliberately omitted; conservative stop-first ordering cannot identify actual intrabar sequence. Gap threshold events do not establish executable fills. No trailing stops, scale-outs, broker connection or account-level risk controls exist.

## Using the trace for later comparison
Run `python -m reference.engine sample_trace.csv --output trace.csv`. Supply matched, precomputed values on consecutive confirmed bars; it starts idle and does not fetch data or compute indicators. Compare its event/level rows to TradingView Bar Replay manually. One matching example is not full parity. See the README for columns and caveats.
