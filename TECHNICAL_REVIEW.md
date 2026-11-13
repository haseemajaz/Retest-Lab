# Technical review — Retest Lab v0.12.0

Review date: 2026-11-13. Scope: source inspection of the Pine prototype, Python reference and trace tools, standalone calculator and its local comparison file, package structure and user-facing interface; synthetic automated tests and local browser checks. This is not a security certification, live market study, TradingView parity test or proof of profitability.

## Findings and actions

| Area | Finding | Action / remaining boundary |
|---|---|---|
| Input integrity | Trace CSV could silently treat some truncated trailing fields as blank; JSON duplicate keys used the last value. | Reject malformed row lengths and duplicate configuration keys. Explicitly blank CSV fields remain valid when permitted. |
| Timestamp order | Valid ISO timestamps could be repeated or backwards while index order remained consecutive. | Preflight warns for adjacent offset-aware instants that repeat or decrease. Blank or naive timestamps break the chain. Trace execution does not enforce time order; cadence, chart mapping and session correctness remain unverified. |
| Tick alignment usability | A generic alignment error did not show what could be changed. | The calculator displays adjacent lower/higher aligned values without editing the form or recommending a choice. Other constraints and market tick rules still apply. |
| Trace file safety | Earlier trace exports replaced an existing output without a prompt; an output hard-linked to an input could also overwrite evidence. | New files are created without clobbering. Existing regular output files require explicit `--force`; input/config paths, aliases and output symlinks are refused. Temporary output is written first. The no-clobber publish step uses a hard link in the destination directory and can fail on filesystems that do not support it. |
| Python validation | Some direct model constraints used `assert`, which disappears under `python -O`. | Constraints and direct OHLC validation use explicit errors. Optimized-mode and malformed CSV/encoding tests were added. |
| Reference tick precision | The Python reference rounds to ten decimal places. A finer configured tick could silently collapse values. | Config now rejects ticks that cannot be represented to ten decimal places. This does **not** make binary-float rounding equivalent to Pine at all magnitudes or boundaries. Compare matched chart examples, particularly half ticks. |
| Calculator arithmetic | Calculator calculations use integer fixed-point arithmetic, not Python's float path. | A separate Python `Decimal` oracle checked 1,200 seeded synthetic long/short examples against JavaScript targets, tick distances, effective R and rounding-change flags. Node is required for this optional cross-language test; this is not Pine parity. |
| Input provenance | Missing session/confirmation flags default to true; enabled filters can be starved of data. | The existing preflight reports these assumptions. It cannot verify feed, session, timezone, sufficient warm-up or source accuracy. |
| State and bars | The reference starts idle, requires consecutive confirmed bars and uses supplied prior values; Pine calculates indicators from chart history. | Supply matched data and sufficient history. Inspect entry, expiry, session/day reset, stop-first ties and fill-bar target omission in replay. Synthetic reference tests are not independent Pine validation. |
| Persistence and privacy | Comparison scenarios live in browser memory until explicitly saved; restore replaces the comparison only after confirmation. | Use the local JSON backup; CSV is export-only. No account sync or broker connection. Files are readable by anyone who has them. |
| Presentation and access | Prior package lacked a local visual entry point. | `START_HERE.html` and the redesigned calculator work locally without a network request in tested flows. The screenshot is historical v0.2, not evidence for v0.3. |
| Reproducibility | A ZIP cannot contain an HTML page that embeds that same final ZIP without recursive packaging. | The package includes `website.template` and `build_site.py`: rebuild the single-file site from the outer ZIP and included guide. `SHA256SUMS` checks included file integrity; it is not a digital signature. |

## What remains unverified

- The unchanged v0.3 Pine source has not been compiled, replayed, or realtime alert-tested in TradingView. The Basic chart previously had both indicator slots occupied; existing work was not removed. See `TEST_PLAN.md` for the acceptance matrix and prerequisites.
- Alert output and broker fills were not tested; alerts are notifications only. OHLC cannot resolve intrabar sequence. Fill-bar targets are deliberately omitted and stop-first treatment is a conservative convention, not observed execution.
- Cross-market/timeframe forward paper observation and independently designed out-of-sample research with spreads, commissions, slippage, gaps and execution assumptions remain to be done. No win-rate, prop-firm compliance or profit claim is supported.
- Browser checks cover selected Chromium desktop/mobile, light/dark, calculator and local file workflows, not all browsers or assistive technologies. The exact HTML layouts may vary by device.

## Reproduce local checks

- `python -m unittest discover -s tests -v` (Python 3.10+). The decimal oracle test is skipped if Node is unavailable; the core Python tools otherwise use the standard library only.
- `node --test tests/*.cjs` (Node 18+).
- `python -m reference.preflight sample_trace.csv --strict` intentionally reports sample assumptions and exits 1. It uses the same Python model, not an independent verification.
- `sha256sum -c SHA256SUMS` from the extracted package on systems with that utility. Hashes identify bundled bytes, not publisher identity.
