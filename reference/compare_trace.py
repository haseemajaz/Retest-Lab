"""Compare manually recorded observations with a Retest Lab reference trace.

This compares only supplied cells. It does not fetch data or run Pine, prove
parity or verify trading performance. An optional checklist reports missing
planned cells; it cannot establish whether the checklist is complete or true.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import sys

FIELDS = ('timestamp', 'day', 'state_before', 'state', 'events', 'cancel_reason',
          'direction', 'entry', 'stop', 't1', 't2', 't3', 't4', 'fills_today', 'targets_hit')
NUMERIC = {'direction', 'entry', 'stop', 't1', 't2', 't3', 't4', 'fills_today'}


def read_csv(path, required, exact=False, allow_empty=False):
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
        if not rows and not allow_empty: raise ValueError(f'{path}: no data rows')
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


def compare_detailed(trace_path, observations_path, allow_empty_observations=False):
    trace = {}
    for line, row in read_csv(trace_path, ('index', *FIELDS)):
        index = index_value(row['index'], f'trace row {line}')
        if index in trace: raise ValueError(f'trace row {line}: duplicate index {index}')
        trace[index] = row
    seen = set()
    differences = []
    count = 0
    for line, row in read_csv(observations_path, ('index', 'field', 'value'), exact=True, allow_empty=allow_empty_observations):
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
    return count, differences, set(trace), seen


def compare(trace_path, observations_path):
    """Keep the original two-value interface for existing callers."""
    count, differences, _, _ = compare_detailed(trace_path, observations_path)
    return count, differences


def read_requirements(path, trace_indexes):
    required = set()
    for line, row in read_csv(path, ('index', 'field'), exact=True):
        index = index_value(row['index'], f'checklist row {line}')
        field = row['field'].strip()
        if field not in FIELDS: raise ValueError(f'checklist row {line}: unknown field {field!r}')
        if index not in trace_indexes: raise ValueError(f'checklist row {line}: index {index} not present in trace')
        if (index, field) in required: raise ValueError(f'checklist row {line}: duplicate index/field {index}/{field}')
        required.add((index, field))
    return required


def main(argv=None):
    p = argparse.ArgumentParser(description='Compare only manually supplied observations with a reference trace; not proof of Pine parity.')
    p.add_argument('trace', help='CSV output from python -m reference.engine')
    p.add_argument('observations', help='manually recorded index,field,value CSV')
    p.add_argument('--required', help='optional planned-observation checklist CSV: index,field')
    args = p.parse_args(argv)
    try:
        count, differences, indexes, seen = compare_detailed(args.trace, args.observations, allow_empty_observations=args.required is not None)
        required = read_requirements(args.required, indexes) if args.required is not None else set()
        missing = sorted(required - seen)
    except (OSError, ValueError, UnicodeError, csv.Error) as exc:
        print(f'Comparison error: {exc}', file=sys.stderr); return 2
    print(f'Compared {count} recorded cell(s); {len(differences)} difference(s). Unrecorded cells were not checked.')
    covered_bars = len({index for index, _ in seen})
    print(f'Observations present on {covered_bars} of {len(indexes)} trace bar(s); presence does not imply correctness or completeness.')
    for field in FIELDS:
        covered = sum(1 for _, f in seen if f == field)
        if covered: print(f'  {field}: {covered} of {len(indexes)} trace bar(s)')
    if args.required is not None:
        print(f'Checklist: {len(required) - len(missing)} of {len(required)} planned cell(s) recorded; {len(missing)} missing.')
        for index, field in missing[:30]: print(f'missing: index {index}, {field}')
        if len(missing) > 30: print(f'... and {len(missing) - 30} more missing cell(s).')
        print('Checklist coverage cannot verify observation accuracy or whether the plan is complete.')
    for index, field, expected, observed in differences:
        print(f'index {index}, {field}: reference={expected!r}; observed={observed!r}')
    print('A match is not proof of Pine parity, execution or trading performance.')
    return 1 if differences or missing else 0


if __name__ == '__main__':
    raise SystemExit(main())
