"""Per-setup outcomes from a reference trace.

A trace is a flat list of bars. A ledger groups it into setups: each setup
starts on a bar with an armed_long or armed_short event and ends on the
first later bar that stops, reaches target 4, or is cancelled, or is still
open when the trace ends. The ledger reports what the model did with each
setup -- filled or not, how many targets were reached, how it ended -- so a
trace can be read setup by setup instead of bar by bar.

This is a summary of modeled threshold events, not a trading record. It
calculates no win rate, return, or profitability, and a flagged (ambiguous)
bar's outcome is a modelling convention, not an observed sequence. Ambiguous
bars are counted on the setup they belong to so they are never silently
folded into an outcome.
"""
import argparse
import csv
import sys

REQUIRED = {'index', 'timestamp', 'day', 'state_before', 'state', 'events',
            'cancel_reason', 'direction', 'entry', 'stop', 't1', 't2', 't3',
            't4', 'fills_today', 'targets_hit', 'order_ambiguity',
            'reject_reason'}
LEDGER_FIELDS = ['setup', 'day', 'direction', 'armed_index', 'end_index',
                 'bars_held', 'entry', 'stop', 'target_1', 'target_2',
                 'target_3', 'target_4', 'fill_index', 'targets_hit',
                 'outcome', 'cancel_reason', 'ambiguous_bars']


def _events(row):
    return [e for e in str(row.get('events') or '').split('|') if e.strip()]


def _hit_set(row):
    hits = set()
    for part in str(row.get('targets_hit') or '').split('|'):
        part = part.strip()
        if part.isdigit():
            hits.add(int(part))
    return hits


def _text(value):
    # Numeric trace values can legitimately be 0; only a missing value is blank.
    return '' if value is None else str(value)


def _index(row):
    raw = row.get('index')
    if raw is None:
        raise ValueError('trace index must be a nonnegative integer')
    raw = str(raw).strip()
    if not raw.isdigit():
        raise ValueError('trace index must be a nonnegative integer')
    return int(raw)


def build_setups(rows):
    """Group trace rows into setups. Rows must be in trace order."""
    rows = list(rows)
    for row in rows:
        if not REQUIRED.issubset(row.keys()):
            missing = sorted(REQUIRED - set(row.keys()))
            raise ValueError('trace missing required columns: ' + ', '.join(missing))
    setups = []
    current = None
    last_index = None
    for row in rows:
        index = _index(row)
        if last_index is not None and index <= last_index:
            raise ValueError('trace indexes must increase')
        last_index = index
        events = _events(row)
        if current is None:
            if 'armed_long' in events or 'armed_short' in events:
                direction = 'long' if 'armed_long' in events else 'short'
                current = {
                    'setup': len(setups) + 1,
                    'day': str(row.get('day') or ''),
                    'direction': direction,
                    'armed_index': index,
                    'end_index': '',
                    'bars_held': 0,
                    'entry': _text(row.get('entry')),
                    'stop': _text(row.get('stop')),
                    'target_1': _text(row.get('t1')),
                    'target_2': _text(row.get('t2')),
                    'target_3': _text(row.get('t3')),
                    'target_4': _text(row.get('t4')),
                    'fill_index': '',
                    'targets_hit': '',
                    'outcome': 'open',
                    'cancel_reason': '',
                    'ambiguous_bars': 0,
                    '_hits': set(),
                }
            else:
                continue
        if str(row.get('order_ambiguity') or '').strip():
            current['ambiguous_bars'] += 1
        current['_hits'] |= _hit_set(row)
        if 'modeled_fill' in events and not current['fill_index']:
            current['fill_index'] = index
        if 'target_4' in events:
            current['outcome'] = 'all_targets'
        elif 'stop' in events:
            current['outcome'] = 'stop'
        elif 'cancelled' in events:
            current['outcome'] = 'cancelled'
            current['cancel_reason'] = str(row.get('cancel_reason') or '')
        if current['outcome'] != 'open':
            current['end_index'] = index
            current['bars_held'] = index - current['armed_index']
            current['targets_hit'] = '|'.join(map(str, sorted(current['_hits'])))
            del current['_hits']
            setups.append(current)
            current = None
    if current is not None:
        current['bars_held'] = last_index - current['armed_index']
        current['targets_hit'] = '|'.join(map(str, sorted(current['_hits'])))
        del current['_hits']
        setups.append(current)
    return setups


def summarize(setups):
    """Counts over finished and open setups; never a win rate."""
    from collections import Counter
    cancelled = Counter(s['cancel_reason'] for s in setups if s['outcome'] == 'cancelled')
    return {
        'total': len(setups),
        'filled': sum(1 for s in setups if s['fill_index'] != ''),
        'open': sum(1 for s in setups if s['outcome'] == 'open'),
        'all_targets': sum(1 for s in setups if s['outcome'] == 'all_targets'),
        'stop': sum(1 for s in setups if s['outcome'] == 'stop'),
        'cancelled': sum(cancelled.values()),
        'cancelled_by_reason': dict(sorted(cancelled.items())),
        'ambiguous_bars': sum(s['ambiguous_bars'] for s in setups),
        'setups_with_ambiguity': sum(1 for s in setups if s['ambiguous_bars']),
    }


def main(argv=None):
    import os
    import tempfile
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Build a per-setup ledger from a reference trace CSV; not a trading record.')
    parser.add_argument('input', help='trace CSV from python -m reference.engine')
    parser.add_argument('--output', help='new ledger CSV (default stdout); existing files require --force')
    parser.add_argument('--force', action='store_true', help='replace an existing regular output file, never the input')
    args = parser.parse_args(argv)
    try:
        if args.force and not args.output:
            raise ValueError('--force requires --output')
        if args.output:
            output = Path(args.output)
            if output.is_symlink():
                raise ValueError('output must not be a symlink')
            source_path = Path(args.input)
            if output.resolve() == source_path.resolve() or (output.exists() and source_path.exists() and output.samefile(source_path)):
                raise ValueError('output must not overwrite input')
            if output.exists() and not args.force:
                raise ValueError('output already exists; choose a new file or use --force')
            if output.exists() and not output.is_file():
                raise ValueError('output must be a regular file')
        with open(args.input, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, strict=True)
            if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
                raise ValueError('trace CSV missing required columns: ' + ', '.join(sorted(REQUIRED - set(reader.fieldnames or []))))
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError('duplicate CSV headers')
            setups = build_setups(reader)
        summary = summarize(setups)
        if args.output:
            fd, temp_name = tempfile.mkstemp(prefix='.retest-ledger-', suffix='.tmp', dir=output.parent)
            try:
                with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
                    writer.writeheader()
                    writer.writerows(setups)
                if output.is_symlink():
                    raise ValueError('output must not be a symlink')
                if args.force:
                    if output.exists() and not output.is_file():
                        raise ValueError('output must be a regular file')
                    os.replace(temp_name, output)
                else:
                    os.link(temp_name, output)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=LEDGER_FIELDS)
            writer.writeheader()
            writer.writerows(setups)
        by_reason = ', '.join(f'{reason}: {n}' for reason, n in summary['cancelled_by_reason'].items())
        print(f"{summary['total']} setup(s): {summary['all_targets']} reached all targets, "
              f"{summary['stop']} stopped, {summary['cancelled']} cancelled"
              + (f" ({by_reason})" if by_reason else "") +
              f", {summary['open']} still open. Filled: {summary['filled']} of {summary['total']}. "
              f"Ambiguous bars inside setups: {summary['ambiguous_bars']}.")
        return 0
    except (OSError, ValueError, TypeError, UnicodeError, csv.Error) as exc:
        print('Ledger error: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
