"""Compare manually recorded observations with a Retest Lab reference trace.

This compares only supplied cells. It does not fetch data or run Pine, prove
parity, detect missing observations, or verify trading performance.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import sys

FIELDS = ('timestamp', 'day', 'state_before', 'state', 'events', 'cancel_reason',
          'direction', 'entry', 'stop', 't1', 't2', 't3', 't4', 'fills_today', 'targets_hit')
NUMERIC = {'direction', 'entry', 'stop', 't1', 't2', 't3', 't4', 'fills_today'}


def read_csv(path, required, exact=False):
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, strict=True)
        header = reader.fieldnames
        if not header or len(header) != len(set(header)):
            raise ValueError(f'{path}: missing or duplicate headers')
        if not set(required).issubset(header) or (exact and set(header) != set(required)):
            raise ValueError(f'{path}: expected {"exactly " if exact else "at least "}columns {", ".join(required)}')
        rows = []
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f'{path}: malformed CSV row {line}')
            rows.append((line, row))
        if not rows: raise ValueError(f'{path}: no data rows')
        return rows


def index_value(raw, label):
    raw = raw.strip()
    if not raw.isascii() or not raw.isdigit(): raise ValueError(f'{label}: index must be a nonnegative integer')
    return int(raw)


def number(raw, label):
    try: n = Decimal(raw)
    except InvalidOperation as exc: raise ValueError(f'{label}: invalid numeric value') from exc
    if not n.is_finite(): raise ValueError(f'{label}: numeric value must be finite')
    return n


def compare(trace_path, observations_path):
    trace = {}
    for line, row in read_csv(trace_path, ('index', *FIELDS)):
        index = index_value(row['index'], f'trace row {line}')
        if index in trace: raise ValueError(f'trace row {line}: duplicate index {index}')
        trace[index] = row
    seen = set()
    differences = []
    count = 0
    for line, row in read_csv(observations_path, ('index', 'field', 'value'), exact=True):
        index = index_value(row['index'], f'observation row {line}')
        field, observed = row['field'].strip(), row['value'].strip()
        if field not in FIELDS: raise ValueError(f'observation row {line}: unknown field {field!r}')
        if index not in trace: raise ValueError(f'observation row {line}: index {index} not present in trace')
        if (index, field) in seen: raise ValueError(f'observation row {line}: duplicate index/field {index}/{field}')
        seen.add((index, field)); count += 1
        expected = trace[index][field].strip()
        if field in NUMERIC:
            a = number(expected, f'trace index {index} {field}') if expected else None
            b = number(observed, f'observation row {line}') if observed else None
            same = a == b
        else: same = expected == observed
        if not same: differences.append((index, field, expected, observed))
    return count, differences


def main(argv=None):
    p = argparse.ArgumentParser(description='Compare only manually supplied observations with a reference trace; not proof of Pine parity.')
    p.add_argument('trace', help='CSV output from python -m reference.engine')
    p.add_argument('observations', help='manually recorded index,field,value CSV')
    args = p.parse_args(argv)
    try:
        count, differences = compare(args.trace, args.observations)
    except (OSError, ValueError, UnicodeError, csv.Error) as exc:
        print(f'Comparison error: {exc}', file=sys.stderr); return 2
    print(f'Compared {count} recorded cell(s); {len(differences)} difference(s). Unrecorded cells were not checked.')
    for index, field, expected, observed in differences:
        print(f'index {index}, {field}: reference={expected!r}; observed={observed!r}')
    print('A match is not proof of Pine parity, execution or trading performance.')
    return 1 if differences else 0


if __name__ == '__main__':
    raise SystemExit(main())
