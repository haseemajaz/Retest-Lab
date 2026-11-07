# Retest Lab v0.3.0 — experimental research prototype

An independent, editable TradingView Pine v6 displacement-and-retest indicator and Python reference. Not Auction Retest Pro, its private code, a broker bot, a performance backtest, or a trading recommendation. Trading involves loss; use paper observation first.

## What is new
- Optional minimum breakout distance as a multiple of previous-bar ATR (default 0, preserving the earlier breakout rule).
- Optional retest-side close confirmation (default OFF). A bar must span entry and close at or above entry for longs, at or below for shorts. The model records the touched level retrospectively at bar close, not an executable fill or guaranteed price.
- Optional session VWAP direction filter (default OFF): confirmed breakout close strictly above/below TradingView's built-in `ta.vwap(hlc3)`. Missing VWAP fails the filter. This is an independent interpretation, not the creator’s implementation. Feed volume, session/anchor and timeframe affect it; especially evaluate on intraday standard candles. EMA and prior relative-volume filters remain available, also off by default. All enabled filters must pass.
- Cancel reason, last-event dashboard, optional markers/levels, and long/short-specific named alerts. JSON schema is now `retest_lab.v3` with `cancel_reason` string or null; recreate all alerts when changing source or inputs.

## Installation and testing
1. Download the ZIP and Word guide from https://haseemajaz.github.io/Retest-Lab/ or copy `retest_lab.pine` from this repository.
2. Open a standard time-based candlestick chart, Pine Editor → new indicator, replace its text, then Add to chart. Settings → Inputs lets you turn on filters. This version still needs a TradingView compile and replay check.
3. The account currently has two occupied indicator slots, so adding v0.3 was blocked. It also previously reported its one-saved-script limit. Preserve/back up existing indicators and scripts; free a slot only if you decide, or use your own plan options. No upgrade or removal was performed.
4. Validate with Bar Replay and paper observation; follow `VALIDATION.md`. Alerts run in real time, not replay. A modeled entry at close may be unavailable. Never connect alerts to orders without independently engineered safeguards.

## Rules in brief
On a confirmed breakout bar, close strictly breaks the preceding 20-bar high/low; candle body >= 0.8 prior ATR and close lies in the outer 25% of the bar. Optional breakout distance is measured beyond the boundary in prior ATR. Entry is the tick-rounded broken boundary; stop is the breakout extreme plus a 0.1 prior-ATR buffer. Require valid tick geometry and risk between 0.25 and 3.0 prior ATR. Arm for up to 10 subsequent bars. Pending cancellation precedence: calendar-day rollover, out of session, expiry, stop breached. Otherwise entry must be spanned; optional close confirmation further restricts it. Gaps that do not span entry are not modeled fills. No target is recorded on the fill bar because OHLC cannot order events. On later bars stop wins over targets, and 0.6R/1R/1.5R/2R thresholds are recorded once. T4 ends the model. Cooldown: 5 full bars after termination; cap: 3 modeled fills/calendar day. Pending setups cancel at session/day boundaries, active setups persist. These threshold observations are not orders or P&L; gaps and partial exits are not execution simulations.

## Validation and limitations
52 synthetic Python tests passed. Python receives precomputed range, ATR, EMA, VWAP and volume; it neither compiles Pine nor proves parity or profitability. v0.2 compiled on AAPL 1D and advanced five replay bars; v0.3 has **not** been compiled, replayed, or alert-tested in TradingView due to the account's occupied chart slots. No cross-market evaluation, forward paper study or independently verified performance. See `VALIDATION.md`.

## Local tests
`python -m unittest discover -s tests -v` (Python 3.10+, standard library). The site embeds ZIP and DOCX in its HTML because GitHub's upload UI rejected binary uploads; it reconstructs the files in your browser. Pine and reference/test source are readable in the repository. See `SOURCES.md` for video evidence and `LICENSE` for project terms.
