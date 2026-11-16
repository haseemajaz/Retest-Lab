"""Compare Pine indicator defaults with the Python reference config.

Pine is the chart runtime; Python is the offline reference. They are
written separately, so a setting can drift in one and not the other.
This read-only check parses the Pine ``input.*`` defaults and compares
the fields both sides share. It does not compile Pine, run a chart, or
prove the two behave the same on real bars. Pine-only settings
(lookback, ATR/EMA/volume lengths, session, timezone, display) are
listed, not compared, because Python receives those values prepared.
"""
import argparse
import json
import re
import sys
from dataclasses import asdict

from reference.engine import Config, load_config

# Pine variable name -> (Python Config field, kind). Targets are handled
# as a group because Pine has four separate inputs.
MAPPED = {
    'bodyMult': ('body_mult', 'float'),
    'edge': ('edge', 'float'),
    'minBreakAtr': ('min_break_atr', 'float'),
    'longs': ('longs', 'bool'),
    'shorts': ('shorts', 'bool'),
    'useEma': ('use_ema', 'bool'),
    'useVwap': ('use_vwap', 'bool'),
    'useVolume': ('use_volume', 'bool'),
    'volMult': ('vol_mult', 'float'),
    'confirmRetest': ('confirm_retest', 'bool'),
    'expiry': ('expiry', 'int'),
    'stopBuffer': ('stop_buffer', 'float'),
    'minRisk': ('min_risk', 'float'),
    'maxRisk': ('max_risk', 'float'),
    'cooldown': ('cooldown', 'int'),
    'cap': ('cap', 'int'),
}
TARGET_INPUTS = ('r1', 'r2', 'r3', 'r4')
PINE_ONLY = ('lookback', 'atrLen', 'emaLen', 'volLen', 'sessionFilter',
             'sessionHours', 'tz', 'showDashboard', 'showVwap', 'showEma',
             'showLevels', 'showMarkers', 'showBackground')

INPUT_RE = re.compile(
    r'input\.(int|float|bool|string|session)\s*\(\s*([^,\)]+)\s*,\s*"([^"]+)"')


def _value(kind, raw):
    raw = raw.strip()
    if kind == 'bool':
        if raw not in ('true', 'false'):
            raise ValueError(f'unsupported bool default: {raw}')
        return raw == 'true'
    if kind == 'int':
        return int(raw)
    if kind == 'float':
        return float(raw)
    return raw.strip('"')


def parse_pine_inputs(path):
    """Return {variable_name: (kind, default)} for Pine input.* lines."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    found = {}
    for line in text.splitlines():
        line = line.strip()
        if 'input.' not in line or '=' not in line:
            continue
        name, _, rest = line.partition('=')
        name = name.strip().split()[-1]
        m = INPUT_RE.search(rest)
        if not m:
            continue
        kind, raw, _label = m.groups()
        found[name] = (kind, _value(kind, raw))
    if not found:
        raise ValueError('no Pine inputs found; is this the indicator source?')
    return found


def compare(pine_path, cfg=None):
    """Return (differences, pine_only, python_only_notes).

    differences: list of (field, pine_value, python_value).
    """
    cfg = cfg or Config()
    inputs = parse_pine_inputs(pine_path)
    py = asdict(cfg)
    differences = []
    for pine_name, (field, _kind) in MAPPED.items():
        if pine_name not in inputs:
            differences.append((field, '<missing in Pine>', py[field]))
            continue
        pine_value = inputs[pine_name][1]
        if pine_value != py[field]:
            differences.append((field, pine_value, py[field]))
    targets = tuple(inputs[n][1] for n in TARGET_INPUTS if n in inputs)
    if len(targets) != 4:
        differences.append(('targets', '<missing Pine target inputs>', py['targets']))
    elif targets != tuple(py['targets']):
        differences.append(('targets', targets, tuple(py['targets'])))
    pine_only = sorted(n for n in inputs if n not in MAPPED and n not in TARGET_INPUTS)
    return differences, pine_only, inputs


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Compare Pine input defaults with the Python reference config; does not compile Pine or prove parity.')
    parser.add_argument('--pine', default='retest_lab.pine', help='Pine indicator source')
    parser.add_argument('--config', help='optional Python config JSON (defaults otherwise)')
    parser.add_argument('--json', action='store_true', help='print machine-readable JSON')
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        differences, pine_only, inputs = compare(args.pine, cfg)
    except (OSError, ValueError, TypeError) as exc:
        print(f'Parity error: {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({'differences': [{'field': f, 'pine': p, 'python': q}
                                        for f, p, q in differences],
                          'pine_only_inputs': pine_only,
                          'pine_inputs_found': sorted(inputs)}, indent=2, default=str))
    else:
        if differences:
            print(f'{len(differences)} difference(s) between Pine defaults and Python config:')
            for field, pine_value, python_value in differences:
                print(f'  {field}: Pine={pine_value!r} Python={python_value!r}')
        else:
            print('Pine defaults and Python config agree on every shared field.')
        if pine_only:
            print('Pine-only inputs (no Python equivalent; check manually): ' + ', '.join(pine_only))
        print('Note: tick is syminfo.mintick in Pine; set the Python tick to match the instrument manually.')
        print('A match is not proof of Pine parity on real bars; it only shows the settings agree.')
    return 1 if differences else 0


if __name__ == '__main__':
    raise SystemExit(main())
