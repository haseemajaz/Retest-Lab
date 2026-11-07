# Retest Lab v0.2.0 — independent research prototype

An educational TradingView Pine v6 displacement-and-retest indicator, plus an executable Python reference. Not Auction Retest Pro, not its source code, not affiliated with the video creator, and not evidence of profitability. The video player and captions could not be reviewed, so this is not a reconstruction. TradingView is the indicator runtime; this project is not an app that executes trades.

## What's new
- Optional trend filter: the confirmed breakout close must be above the same-bar EMA for longs, below it for shorts. Defaults off.
- Optional relative-volume filter: breakout-bar volume must be at least a configurable multiple of the preceding N-bar volume average. Missing/zero volume or an unwarmed average rejects setups when enabled. Defaults off.
- Dashboard adds direction, remaining pending bars, active filter status; display toggles for EMA, dashboard and pending background.
- Ambiguous fill-bar target fix: target events are deferred until a *later* bar, because OHLC does not reveal whether a target came before or after the retest. This can miss genuine fill-bar target hits. Pending stop invalidation still wins over fills; active stop wins over targets on later bars.
- JSON alert schema changed to `retest_lab.v2`; recreate TradingView alerts after code/settings changes. Named alert conditions are also available.

## TradingView installation
1. Open `retest_lab.pine`, copy all text. On a standard time-based candlestick chart open Pine Editor.
2. Create a **new indicator**, replace the sample text, paste the source, and choose Add to chart. Save if your account has a free script slot.
3. If TradingView says the saved-script limit is reached, free a slot only after backing up your existing script, or consider your own plan options. Do not remove someone else's script. Until saved, the editor contents may be lost.
4. Enable optional filters via indicator Settings → Inputs. EMA and volume filters start OFF; enable individually to compare signals. A filter is not a profitability guarantee.
5. Test using Bar Replay and paper observation. Read `Retest_Lab_v0.2_Guide.docx` and `VALIDATION.md` before using alerts.

## Rules in brief
On a confirmed breakout bar, close must break the preceding 20-bar high/low, candle body >= 0.8 previous ATR and close in the outer 25% of its range. Set entry at the broken boundary, stop beyond the breakout candle with a 0.1 prior-ATR buffer. Require correct tick-rounded stop/target geometry and risk 0.25–3.0 prior ATR. Arm for up to 10 following bars; never fill the breakout bar. Exact entry touch models a fill unless the pending bar already breaches stop, session, date or expiry rules. No targets reported on fill bar. On later active bars stop takes precedence, then targets at 0.6R, 1R, 1.5R, 2R are noted once. T4 terminates. These are threshold observations, not executable fills. Five full cooldown bars; max three modeled fills/day, calendar and session timezone UTC by default. Active setup stays after session end; pending cancels.

## Alerts and important limitations
Create Alert → this indicator → “Any alert() function call” for dynamic JSON, or choose one of the named alert conditions. Events trigger on completed bars only. An entry identified at bar close may no longer be available. Alerts are snapshots; recreate after changes. No order routing, portfolio limits, loss limits, trade sizing, slippage, spread, partial exits, commissions, news filter or prop-firm compliance. Candlestick OHLC cannot establish intrabar order. Use standard time-based charts and validate market/feed/timezone settings. The model is not a backtest and does not estimate returns.

## Validation
On 2026-11-07, v0.2 compiled and displayed on TradingView AAPL 1D in an authenticated chart. A short Bar Replay smoke test advanced five daily bars without a visible runtime error. This is not comprehensive correctness validation. TradingView saving was blocked by the account's existing one-saved-script limit, so do not assume the indicator was saved. The Python suite passes 35 synthetic unit tests; it does not compile Pine or independently prove Pine/Python parity. See VALIDATION.md.

## Local testing
`python -m unittest discover -s tests -v` (Python 3.10+, no external packages). See reference/engine.py. Caller supplies indicator data (prior ATR/range, same-bar EMA, current volume and prior volume average); it is not a market-data importer or a performance backtester.

## Repository and downloads
The project website at https://haseemajaz.github.io/Retest-Lab/ provides the software ZIP and Word guide. Binary downloads are embedded in the site HTML because the GitHub file-upload interface failed in the authoring environment; JavaScript reconstructs the original files on download. The ZIP contains the full source, guide, reference and tests.

## Files in the software ZIP
`retest_lab.pine`, `reference/engine.py`, `tests/test_engine.py`, `test_results.txt`, `VALIDATION.md`, `SOURCES.md`, `LICENSE`, `Retest_Lab_v0.2_Guide.docx`.
