"""Inspect prepared trace inputs, not market quality or TradingView parity."""
import argparse
import csv
from datetime import datetime
import json
import sys

from reference.engine import load_config, trace_rows

REQUIRED = {'index', 'day', 'open', 'high', 'low', 'close', 'prior_high', 'prior_low', 'prior_atr'}


def blank(value):
    return value is None or not str(value).strip()


def inspect(path, config_path=None):
    """Validate using the trace model, then report narrowly scoped warnings.

    Returns (bar_count, warnings), where each warning is (description, indexes).
    Calls the same model as the trace; this is not independent validation.
    """
    cfg = load_config(config_path)
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, strict=True)
        names = reader.fieldnames
        if not names or not REQUIRED.issubset(names):
            raise ValueError('CSV missing required columns: ' + ', '.join(sorted(REQUIRED - set(names or []))))
        if len(names) != len(set(names)): raise ValueError('duplicate CSV headers')
        rows = list(reader)
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError('malformed CSV row (wrong number of fields)')
    if not rows: raise ValueError('CSV has no bars')
    # Same processing as the trace CLI; model-generated events are not evidence.
    trace_rows(rows, cfg)
    warnings = []
    def warn(message, selected):
        indexes = [int(row['index'].strip()) for row in selected]
        if indexes: warnings.append((message, indexes))
    warn('in_session blank or absent: trace assumes true', [r for r in rows if blank(r.get('in_session'))])
    warn('confirmed blank or absent: trace assumes true', [r for r in rows if blank(r.get('confirmed'))])
    warn('timestamp blank or absent: chart-bar mapping cannot be checked', [r for r in rows if blank(r.get('timestamp'))])
    warn('timestamp has no timezone offset: mapping can be ambiguous', [r for r in rows if not blank(r.get('timestamp')) and datetime.fromisoformat(r['timestamp'].strip().replace('Z', '+00:00')).utcoffset() is None])
    unprepared = [r for r in rows if blank(r.get('prior_atr'))]
    warn('prior high/low/ATR blank: breakout detection is skipped', unprepared)
    zero_atr = [r for r in rows if not blank(r.get('prior_atr')) and float(r['prior_atr']) == 0]
    warn('prior ATR is zero: breakout detection is skipped', zero_atr)
    ready = [r for r in rows if not blank(r.get('prior_atr')) and float(r['prior_atr']) > 0]
    if cfg.use_ema:
        warn('EMA filter enabled but EMA missing: a candidate would be rejected', [r for r in ready if blank(r.get('ema'))])
    if cfg.use_vwap:
        warn('VWAP filter enabled but VWAP missing: a candidate would be rejected', [r for r in ready if blank(r.get('vwap'))])
    if cfg.use_volume:
        warn('volume filter enabled but volume or prior average missing: a candidate would be rejected', [r for r in ready if blank(r.get('volume')) or blank(r.get('prior_volume_avg'))])
        warn('volume filter enabled but prior volume average is zero: a candidate would be rejected', [r for r in ready if not blank(r.get('prior_volume_avg')) and float(r['prior_volume_avg']) == 0])
    return len(rows), warnings


def main(argv=None):
    p = argparse.ArgumentParser(description='Check prepared bars for trace-input issues; does not independently validate Pine or market data.')
    p.add_argument('input', help='prepared bar CSV for reference.engine')
    p.add_argument('--config', help='optional JSON overrides, as used for reference.engine')
    p.add_argument('--strict', action='store_true', help='return status 1 when any warning is present')
    args = p.parse_args(argv)
    try:
        count, warnings = inspect(args.input, args.config)
    except (OSError, UnicodeError, ValueError, TypeError, csv.Error, json.JSONDecodeError) as exc:
        print(f'Preflight error: {exc}', file=sys.stderr); return 2
    print(f'Validated {count} bar(s) with the Python trace model; {len(warnings)} warning category(s).')
    for message, indexes in warnings:
        example = ', '.join(map(str, indexes[:5]))
        suffix = ', ...' if len(indexes) > 5 else ''
        print(f'WARNING: {message} — {len(indexes)} bar(s); indexes: {example}{suffix}')
    print('No chart, feed, warm-up sufficiency, timezone mapping, Pine parity or performance was verified.')
    return 1 if args.strict and warnings else 0


if __name__ == '__main__':
    raise SystemExit(main())
