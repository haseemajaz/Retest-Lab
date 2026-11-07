# Validation record — v0.3.0

## Completed
- 2026-11-07: 52 Python synthetic unit tests pass (`python -m unittest discover -s tests -v`); `test_results.txt` records the output. The Python reference takes prepared indicators rather than obtaining market data. These tests do not compile Pine, independently validate parity, or measure trading returns.
- v0.2 compiled and displayed on an AAPL daily chart and a five-bar Bar Replay smoke test showed no visible runtime error. That was v0.2, NOT this release.
- A v0.3 TradingView Add to chart attempt was blocked before a successful chart test: the Basic plan chart already contained the two permitted indicators. Create new layout also reported the one-layout plan limit. Existing chart indicators were not removed. Earlier saving v0.2 was blocked by the one-saved-script limit. v0.3 is not confirmed saved.
- The video transcript was read on 2026-11-07; the video player did not load. Auto captions can mis-transcribe technical terms, and no visuals or trading records were independently verified.

## Still required before reliance
- Compile and add v0.3 on a standard candlestick chart once a slot is available, then replay long/short, minimum-distance and close-confirmation boundaries, filters including missing volume/VWAP, stop/target ties, expiry, day/session changes, cooldown/cap and ticks. Compare to Python with matched inputs and recorded bars.
- Test real-time named and v3 JSON alerts separately, without broker routing; alerts do not fire on historical/replay bars. Check snapshots and cancel_reason.
- Cross-market/timeframe paper observation, then independently designed out-of-sample research with commissions, spread, slippage and realistic order execution. No win-rate claim is validated. Never interpret indicator results as compliance with a prop firm's rules.
- Fill-bar targets deliberately omitted; conservative stop-first ordering cannot identify actual intrabar sequence. Gap threshold events do not establish executable fills. No trailing stops, scale-outs, broker connection or account-level risk controls exist.
