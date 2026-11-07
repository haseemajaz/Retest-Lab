# Validation record — v0.2.0

## Completed
- 2026-11-07: `python -m unittest discover -s tests -v`: 35 synthetic tests pass; captured in `test_results.txt`.
- 2026-11-07: Pine v6 source pasted into TradingView under user-authorized account, compiled and added to an AAPL daily chart. Historical arming markers and dashboard rendered; no visible compilation or runtime error on that chart.
- 2026-11-07: Bar Replay on AAPL 1D advanced five bars, with the indicator visible and no visible runtime error. This smoke test did not verify all events, filter combinations, intrabar ordering, alerts or profitability.
- The chart instance was moved to the price pane. No orders or broker actions were performed. A temporary default template indicator was replaced by the prototype.

## Not completed / required before reliance
- TradingView refused to save due to Basic account's one-saved-script limit. The prototype is NOT confirmed saved; unsaved chart/editor state can disappear.
- No exhaustive Pine/Python parity checks; Python receives prepared indicator values. No replay assertion for all lifecycle paths or filter settings. No live alerts, automation, multi-symbol analysis, spread/commission tests, or statistical performance testing.
- No complete video/captions review: YouTube player failed to play in this environment. No claim of replication of private code or actual settings.
- Alerts occur only after bar close and cannot guarantee an actionable entry. OHLC cannot resolve intrabar order; no fill-bar targets are recorded even if the price may actually have hit them after entry.

## Acceptance checklist
1. Save or export existing scripts before freeing any account slot; then save this code as a new script.
2. On standard time-based candles test longs/shorts, volume missing/zero, EMA equality, prior-volume warmup, sessions/day rollover, retest expiry, and cooldown/cap.
3. Replay stop+target overlap, fill+target overlap, gap bars, target ordering and high/low bounds. Compare manually against reference engine on matching synthetic bars and inputs.
4. Verify named and JSON alerts in a test environment; never connect them directly to order execution without independent safeguards.
5. Forward paper-observe multiple instruments/timeframes; include spread, commissions and slippage in any separately built performance study.
