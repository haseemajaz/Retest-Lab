import csv, subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.ledger import build_setups, summarize

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['index', 'timestamp', 'day', 'state_before', 'state', 'events',
          'cancel_reason', 'direction', 'entry', 'stop', 't1', 't2', 't3',
          't4', 'fills_today', 'targets_hit', 'order_ambiguity',
          'reject_reason']


def row(index, events='', **over):
    base = {f: '' for f in FIELDS}
    base.update(index=str(index), timestamp='', day='2026-01-01',
                state_before='idle', state='idle', events=events)
    base.update(over)
    return base


def armed(index, direction='long'):
    return row(index, 'armed_long' if direction == 'long' else 'armed_short',
               state='armed', direction='1' if direction == 'long' else '-1',
               entry='100.0', stop='98.8', t1='100.72', t2='101.2',
               t3='101.8', t4='102.4')


class LedgerTests(unittest.TestCase):
    def test_all_targets_setup(self):
        setups = build_setups([armed(20), row(21, 'modeled_fill', state_before='armed', state='active', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4'),
                               row(22, 'target_1|target_2|target_3|target_4', state_before='active', state='idle', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4', targets_hit='1|2|3|4', order_ambiguity='target_order')])
        self.assertEqual(len(setups), 1)
        s = setups[0]
        self.assertEqual((s['outcome'], s['armed_index'], s['end_index'], s['bars_held']), ('all_targets', 20, 22, 2))
        self.assertEqual((s['fill_index'], s['targets_hit'], s['ambiguous_bars']), (21, '1|2|3|4', 1))

    def test_stop_after_partial_targets(self):
        setups = build_setups([armed(28), row(29, 'modeled_fill', state_before='armed', state='active', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4'),
                               row(30, 'target_1', state_before='active', state='active', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4', targets_hit='1'),
                               row(31, 'stop', state_before='active', state='idle', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4', targets_hit='1')])
        self.assertEqual([(s['outcome'], s['targets_hit']) for s in setups], [('stop', '1')])

    def test_cancelled_and_open_setups(self):
        setups = build_setups([armed(37), row(38, '', state_before='armed', state='armed', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4'),
                               row(48, 'cancelled', state_before='armed', state='idle', cancel_reason='expired', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4'),
                               armed(60, 'short')])
        self.assertEqual([(s['outcome'], s['cancel_reason']) for s in setups], [('cancelled', 'expired'), ('open', '')])
        self.assertEqual(setups[1]['bars_held'], 0)  # open: no later bar in this trace

    def test_no_setups(self):
        self.assertEqual(build_setups([row(0), row(1, '', reject_reason='no_breakout')]), [])
        self.assertEqual(summarize([]), {'total': 0, 'filled': 0, 'open': 0, 'all_targets': 0, 'stop': 0, 'cancelled': 0, 'cancelled_by_reason': {}, 'ambiguous_bars': 0, 'setups_with_ambiguity': 0})

    def test_summary_counts(self):
        setups = build_setups([armed(20), row(21, 'modeled_fill', state_before='armed', state='active', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4'),
                               row(22, 'target_1|target_2|target_3|target_4', state_before='active', state='idle', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4', targets_hit='1|2|3|4', order_ambiguity='target_order'),
                               armed(28), row(29, 'cancelled', state_before='armed', state='idle', cancel_reason='expired', direction='1', entry='100.0', stop='98.8', t1='100.72', t2='101.2', t3='101.8', t4='102.4')])
        summary = summarize(setups)
        self.assertEqual((summary['total'], summary['filled'], summary['all_targets'], summary['cancelled']), (2, 1, 1, 1))
        self.assertEqual(summary['cancelled_by_reason'], {'expired': 1})
        self.assertEqual((summary['ambiguous_bars'], summary['setups_with_ambiguity']), (1, 1))

    def test_integer_index_zero_is_valid(self):
        # Trace rows carry int indexes; 0 is a real index, not a missing value.
        rows = [row(0), row(1)]
        for r in rows:
            r['index'] = int(r['index'])
        self.assertEqual(build_setups(rows), [])

    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            build_setups([{'index': '0', 'events': ''}])

    def test_non_increasing_index_rejected(self):
        with self.assertRaises(ValueError):
            build_setups([row(5), row(5)])

    def test_cli_on_sample_trace(self):
        result = subprocess.run([sys.executable, '-m', 'reference.ledger', str(ROOT / 'sample_ledger_trace.csv')], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('3 setup(s): 1 reached all targets, 1 stopped, 1 cancelled (expired: 1), 0 still open', result.stdout)
        self.assertIn('Filled: 2 of 3', result.stdout)
        # stdout starts with the CSV header when no --output is given
        self.assertTrue(result.stdout.startswith('setup,day,direction,armed_index'))
        import re
        csv_lines = [line for line in result.stdout.splitlines() if line.startswith('setup,') or re.match(r'^\d+,2026-', line)]
        data = list(csv.DictReader(csv_lines))
        self.assertEqual([r['outcome'] for r in data], ['all_targets', 'stop', 'cancelled'])
        self.assertEqual([r['armed_index'] for r in data], ['20', '28', '37'])

    def test_cli_refuses_to_overwrite_without_force(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'ledger.csv'
            out.write_text('existing')
            result = subprocess.run([sys.executable, '-m', 'reference.ledger', str(ROOT / 'sample_ledger_trace.csv'), '--output', str(out)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 2)
            self.assertIn('already exists', result.stderr)
            self.assertEqual(out.read_text(), 'existing')


if __name__ == '__main__':
    unittest.main()
