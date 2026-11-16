"""Inspect prepared trace inputs, not market quality or TradingView parity."""
import argparse
import csv
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
import sys

from reference.engine import load_config, trace_rows

REQUIRED = {'index', 'day', 'open', 'high', 'low', 'close', 'prior_high', 'prior_low', 'prior_atr'}
MAX_EXPECTED_SECONDS = 365 * 24 * 60 * 60

def validate_expected_seconds(value):
    if value is not None and (type(value) is not int or not 1 <= value <= MAX_EXPECTED_SECONDS):
        raise ValueError("expected seconds must be an integer from 1 to 31536000")
    return value

OPTIONAL = {'timestamp', 'in_session', 'confirmed', 'ema', 'volume', 'prior_volume_avg', 'vwap'}

def exact_fraction(raw):
    try: number = Decimal(str(raw).strip())
    except InvalidOperation as exc: raise ValueError('invalid decimal') from exc
    parts = number.as_tuple()
    if not number.is_finite() or len(parts.digits) > 100 or abs(parts.exponent) > 100:
        raise ValueError('decimal outside tick-check bounds')
    return Fraction(number)


def blank(value):
    return value is None or not str(value).strip()


def inspect(path, config_path=None, check_tick=False, expected_seconds=None):
    """Validate using the trace model, then report narrowly scoped warnings.

    Returns (bar_count, warnings), where each warning is (description, indexes).
    Calls the same model as the trace; this is not independent validation.
    """
    validate_expected_seconds(expected_seconds)
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
    unknown = sorted(set(names) - REQUIRED - OPTIONAL)
    if unknown:
        warnings.append(('unrecognized CSV columns ignored by trace: ' + ', '.join(repr(n) for n in unknown), [int(r['index'].strip()) for r in rows]))
    warn('in_session blank or absent: trace assumes true', [r for r in rows if blank(r.get('in_session'))])
    warn('confirmed blank or absent: trace assumes true', [r for r in rows if blank(r.get('confirmed'))])
    warn('timestamp blank or absent: chart-bar mapping cannot be checked', [r for r in rows if blank(r.get('timestamp'))])
    warn('timestamp has no timezone offset: mapping can be ambiguous', [r for r in rows if not blank(r.get('timestamp')) and datetime.fromisoformat(r['timestamp'].strip().replace('Z', '+00:00')).utcoffset() is None])
    # Compare only adjacent rows with two offset-aware timestamps. A blank or
    # naive value breaks the chain; do not invent a timezone or expected cadence.
    repeated, reversed_time = [], []
    for previous, current in zip(rows, rows[1:]):
        a, b = previous.get('timestamp'), current.get('timestamp')
        if blank(a) or blank(b): continue
        first = datetime.fromisoformat(a.strip().replace('Z', '+00:00'))
        second = datetime.fromisoformat(b.strip().replace('Z', '+00:00'))
        if first.utcoffset() is None or second.utcoffset() is None: continue
        if second == first: repeated.append(current)
        elif second < first: reversed_time.append(current)
    warn('adjacent offset-aware timestamps repeat the same instant', repeated)
    warn('adjacent offset-aware timestamps go backwards', reversed_time)
    previous_aware, previous_pos = None, None
    repeated_gap, reversed_gap = [], []
    for pos, row in enumerate(rows):
        raw = row.get('timestamp')
        if blank(raw): continue
        stamp = datetime.fromisoformat(raw.strip().replace('Z', '+00:00'))
        if stamp.utcoffset() is None: continue
        if previous_aware is not None and pos > previous_pos + 1:
            if stamp == previous_aware: repeated_gap.append(row)
            elif stamp < previous_aware: reversed_gap.append(row)
        previous_aware, previous_pos = stamp, pos
    warn('known offset-aware timestamps repeat across missing or naive timestamps', repeated_gap)
    warn('known offset-aware timestamps go backwards across missing or naive timestamps', reversed_gap)
    if expected_seconds is not None:
        # Advisory only. Check adjacent known instants, never invent missing
        # offsets, exchange sessions, trading schedules, or bar cadence.
        expected = timedelta(seconds=expected_seconds)
        if len(rows) < 2:
            warn('cadence not assessed: fewer than two bars', rows)
        shorter, longer, unchecked = [], [], []
        for prev, current in zip(rows, rows[1:]):
            a, b = prev.get('timestamp'), current.get('timestamp')
            if blank(a) or blank(b):
                unchecked.append(current); continue
            first = datetime.fromisoformat(a.strip().replace('Z', '+00:00'))
            second = datetime.fromisoformat(b.strip().replace('Z', '+00:00'))
            if first.utcoffset() is None or second.utcoffset() is None:
                unchecked.append(current); continue
            delta = second - first
            # Zero/negative intervals have their own existing warning.
            if timedelta(0) < delta < expected: shorter.append(current)
            if delta > expected: longer.append(current)
        warn('adjacent timestamp interval shorter than expected; review bar boundaries and source', shorter)
        warn('adjacent timestamp interval longer than expected; market closures and breaks may be normal', longer)
        warn('adjacent timestamp interval not checked: a timestamp is blank or timezone-naive', unchecked)
    if check_tick:
        tick = exact_fraction(str(cfg.tick))
        off_grid, unchecked = [], []
        for row in rows:
            try:
                prices = [exact_fraction(row[field]) for field in ('open', 'high', 'low', 'close')]
                if any((price / tick).denominator != 1 for price in prices): off_grid.append(row)
            except ValueError: unchecked.append(row)
        warn('OHLC off the configured tick grid (exact decimal test); review feed and tick', off_grid)
        warn('OHLC tick-grid check skipped: decimal outside bounded precision', unchecked)
    # This flags visible decimal changes at conversion, not every binary-float
    # representation error or subsequent arithmetic rounding error.
    numeric_fields = ('open','high','low','close','prior_high','prior_low','prior_atr','ema','volume','prior_volume_avg','vwap')
    changed = []
    for row in rows:
        if any(Decimal(str(float(row[k].strip()))) != Decimal(row[k].strip())
               for k in numeric_fields if not blank(row.get(k))):
            changed.append(row)
    warn('decimal input changes when converted to model float; inspect precision', changed)
    large_tick_units = []
    for row in rows:
        if any(abs(float(row[k]) / cfg.tick) >= 2**53
               for k in ('open','high','low','close','prior_high','prior_low') if not blank(row.get(k))):
            large_tick_units.append(row)
    warn('price magnitude at least 2^53 configured ticks; float tick resolution is unsafe', large_tick_units)
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
    p.add_argument('--expected-seconds', type=int, help='optional expected positive adjacent-bar interval in seconds (1 to 31536000); advisory only')
    p.add_argument('--strict', action='store_true', help='return status 1 when any warning is present')
    p.add_argument('--check-tick', action='store_true', help='warn about OHLC off the configured constant tick grid')
    args = p.parse_args(argv)
    try:
        count, warnings = inspect(args.input, args.config, check_tick=args.check_tick, expected_seconds=args.expected_seconds)
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError, csv.Error, json.JSONDecodeError) as exc:
        print(f'Preflight error: {exc}', file=sys.stderr); return 2
    print(f'Validated {count} bar(s) with the Python trace model; {len(warnings)} warning category(s).')
    for message, indexes in warnings:
        example = ', '.join(map(str, indexes[:5]))
        suffix = ', ...' if len(indexes) > 5 else ''
        print(f'WARNING: {message} — {len(indexes)} bar(s); indexes: {example}{suffix}')
    if args.expected_seconds is not None:
        print(f'Advisory cadence: {args.expected_seconds} seconds; closures and session breaks may be normal. Only adjacent offset-aware timestamps were checked.')
    print('No chart, feed, warm-up sufficiency, timezone mapping, Pine parity or performance was verified.')
    return 1 if args.strict and warnings else 0


if __name__ == '__main__':
    raise SystemExit(main())
