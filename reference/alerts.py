"""Validate a Retest Lab v3 alert JSON payload, offline.

The Pine indicator emits one JSON alert per bar close with schema
``retest_lab.v3``. This checker validates the shape only: it cannot
confirm the alert fired on a real chart, that the bar was real, or
that any trade followed. It never contacts TradingView or a broker.
"""
import argparse
import json
import sys
from math import isfinite

KNOWN_EVENTS = {'armed_long', 'armed_short', 'modeled_fill', 'stop', 'cancelled',
                'target_1', 'target_2', 'target_3', 'target_4'}
PRICE_FIELDS = ('entry', 'stop', 't1', 't2', 't3', 't4')
CANCEL_REASONS = {'day_rollover', 'outside_session', 'expired', 'stop_before_fill', None}


def validate(payload):
    """Return a list of problems; empty means the shape is valid."""
    problems = []
    if not isinstance(payload, dict):
        return ['alert must be a JSON object']
    if payload.get('schema') != 'retest_lab.v3':
        problems.append(f"schema must be 'retest_lab.v3', got {payload.get('schema')!r}")
    for field in ('symbol', 'timeframe'):
        if not isinstance(payload.get(field), str) or not payload[field]:
            problems.append(f'{field} must be a non-empty string')
    if type(payload.get('bar_close_ms')) is not int or payload.get('bar_close_ms', 0) < 0:
        problems.append('bar_close_ms must be a nonnegative integer (milliseconds)')
    if payload.get('direction') not in (1, -1):
        problems.append(f"direction must be 1 or -1, got {payload.get('direction')!r}")
    events = payload.get('events')
    if not isinstance(events, list) or not events or any(not isinstance(e, str) for e in events):
        problems.append('events must be a non-empty list of strings')
    else:
        unknown = sorted(set(events) - KNOWN_EVENTS)
        if unknown:
            problems.append(f'unknown events: {", ".join(unknown)}')
        if len(events) != len(set(events)):
            problems.append('events contains duplicates')
        if 'cancelled' in events and payload.get('cancel_reason') is None:
            problems.append('cancelled event requires a cancel_reason')
        if 'cancelled' not in events and payload.get('cancel_reason') is not None:
            problems.append('cancel_reason is set without a cancelled event')
    if payload.get('cancel_reason') not in CANCEL_REASONS:
        problems.append(f"cancel_reason must be one of day_rollover, outside_session, expired, stop_before_fill or null, got {payload.get('cancel_reason')!r}")
    for field in PRICE_FIELDS:
        value = payload.get(field)
        if type(value) not in (int, float) or not isfinite(value):
            problems.append(f'{field} must be a finite number')
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Validate a Retest Lab v3 alert JSON file; shape only, no chart or broker check.')
    parser.add_argument('alert', help='JSON file with one alert payload')
    args = parser.parse_args(argv)
    try:
        with open(args.alert, encoding='utf-8') as f:
            payload = json.load(f)
    except (OSError, ValueError) as exc:
        print(f'Alert error: {exc}', file=sys.stderr)
        return 2
    problems = validate(payload)
    if problems:
        print(f'Invalid alert ({len(problems)} problem(s)):')
        for problem in problems:
            print(f'  - {problem}')
        return 1
    print('Alert shape is valid for schema retest_lab.v3. This does not prove it fired on a real chart.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
