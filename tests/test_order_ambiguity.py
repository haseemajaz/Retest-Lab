import csv
import io
import subprocess
import sys
import unittest
from pathlib import Path

from reference.engine import Bar, Config, Engine, Setup, order_ambiguities, trace_rows

ROOT = Path(__file__).resolve().parents[1]
L = Setup(1, 100, 98, (101.2, 102, 103, 104))
S = Setup(-1, 100, 102, (98.8, 98, 97, 96))


def b(i, low=101, high=102, day='2026-01-01', **kw):
    return Bar(i, day, kw.pop('open', (low + high) / 2), high, low,
               kw.pop('close', (low + high) / 2), **kw)


class PureFunctionTests(unittest.TestCase):
    def test_no_setup_levels(self):
        self.assertEqual(order_ambiguities(1, 100, 98, (101, 102, 103, 104), set(), 99, 105,
                                           was_armed=False, was_active=False, filled_this_bar=False), [])

    def test_armed_fill_vs_stop_long(self):
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, set(), 97, 101,
                                           was_armed=True, was_active=False, filled_this_bar=False),
                         ['fill_vs_stop'])

    def test_armed_fill_vs_stop_short(self):
        self.assertEqual(order_ambiguities(-1, 100, 102, S.targets, set(), 99, 103,
                                           was_armed=True, was_active=False, filled_this_bar=False),
                         ['fill_vs_stop'])

    def test_armed_entry_only_is_not_ambiguous(self):
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, set(), 99, 101,
                                           was_armed=True, was_active=False, filled_this_bar=False), [])

    def test_armed_stop_only_is_not_ambiguous(self):
        # Entry not spanned, so there is no fill the stop could precede.
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, set(), 97, 99,
                                           was_armed=True, was_active=False, filled_this_bar=False), [])

    def test_fill_bar_target(self):
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, set(), 100, 103,
                                           was_armed=True, was_active=False, filled_this_bar=True),
                         ['fill_vs_target'])

    def test_active_stop_vs_target_and_order(self):
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, set(), 97, 105,
                                           was_armed=False, was_active=True, filled_this_bar=False),
                         ['stop_vs_target', 'target_order'])

    def test_active_single_target_no_order_label(self):
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, set(), 97, 101.5,
                                           was_armed=False, was_active=True, filled_this_bar=False),
                         ['stop_vs_target'])

    def test_active_stop_only_is_not_ambiguous(self):
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, set(), 97, 100.5,
                                           was_armed=False, was_active=True, filled_this_bar=False), [])

    def test_active_targets_only_flag_order_not_stop(self):
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, set(), 99, 103,
                                           was_armed=False, was_active=True, filled_this_bar=False),
                         ['target_order'])

    def test_already_hit_targets_do_not_count(self):
        # T1 and T2 were recorded on an earlier bar; only T3 is new here.
        self.assertEqual(order_ambiguities(1, 100, 98, L.targets, {1, 2}, 99, 103,
                                           was_armed=False, was_active=True, filled_this_bar=False), [])

    def test_short_active_stop_vs_target(self):
        self.assertEqual(order_ambiguities(-1, 100, 102, S.targets, set(), 96, 103,
                                           was_armed=False, was_active=True, filled_this_bar=False),
                         ['stop_vs_target', 'target_order'])

    def test_invalid_direction_is_empty(self):
        self.assertEqual(order_ambiguities(0, 100, 98, L.targets, set(), 97, 105,
                                           was_armed=False, was_active=True, filled_this_bar=False), [])


class EngineTests(unittest.TestCase):
    def arm(self, setup=L, cfg=None):
        e = Engine(cfg or Config())
        e.step(b(0), setup)
        return e

    def test_armed_cancel_flagged(self):
        e = self.arm()
        self.assertEqual(e.step(b(1, 97, 101)), ['cancelled'])
        self.assertEqual(e.last_ambiguities, ['fill_vs_stop'])
        self.assertEqual(e.last_cancel_reason, 'stop_before_fill')

    def test_armed_cancel_short_flagged(self):
        e = self.arm(setup=S)
        self.assertEqual(e.step(b(1, 99, 103)), ['cancelled'])
        self.assertEqual(e.last_ambiguities, ['fill_vs_stop'])

    def test_clean_fill_not_flagged(self):
        e = self.arm()
        self.assertEqual(e.step(b(1, 100, 100.5)), ['modeled_fill'])
        self.assertEqual(e.last_ambiguities, [])

    def test_fill_bar_target_flagged_and_deferred(self):
        e = self.arm()
        self.assertEqual(e.step(b(1, 100, 103)), ['modeled_fill'])
        self.assertEqual(e.last_ambiguities, ['fill_vs_target'])
        self.assertEqual(e.hit, set())

    def test_active_stop_vs_target_flagged(self):
        e = self.arm()
        e.step(b(1, 100, 100.5))
        self.assertEqual(e.step(b(2, 97, 105)), ['stop'])
        self.assertEqual(e.last_ambiguities, ['stop_vs_target', 'target_order'])

    def test_day_rollover_cancel_not_flagged_as_price_order(self):
        e = self.arm()
        self.assertEqual(e.step(b(1, 97, 101, day='2026-01-02')), ['cancelled'])
        self.assertEqual(e.last_ambiguities, [])
        self.assertEqual(e.last_cancel_reason, 'day_rollover')

    def test_ambiguity_resets_on_next_bar(self):
        e = self.arm()
        e.step(b(1, 97, 101))
        self.assertEqual(e.last_ambiguities, ['fill_vs_stop'])
        # A later idle bar with no setup must not carry the old label.
        e.step(b(2, 101, 102))
        self.assertEqual(e.last_ambiguities, [])

    def test_no_rearm_inherits_ambiguity(self):
        e = Engine(Config(cooldown=0))
        e.step(b(0), L)
        self.assertEqual(e.step(b(1, 97, 101), L), ['cancelled'])
        self.assertEqual(e.last_ambiguities, ['fill_vs_stop'])


class TraceTests(unittest.TestCase):
    def row(self, i=20, **kwargs):
        d = {'index': str(i), 'day': '2026-01-01', 'open': '99.5', 'high': '102', 'low': '99',
             'close': '101.8', 'prior_high': '100', 'prior_low': '95', 'prior_atr': '2'}
        d.update(kwargs)
        return d

    def test_trace_column_present_and_active_case(self):
        rows = [self.row(),
                self.row(21, open='100.4', high='100.5', low='100', close='100.2',
                         prior_high='', prior_low='', prior_atr=''),
                self.row(22, open='100.5', high='103', low='97', close='102',
                         prior_high='', prior_low='', prior_atr='')]
        out = trace_rows(rows)
        self.assertEqual(out[0]['order_ambiguity'], '')
        self.assertEqual(out[1]['order_ambiguity'], '')
        self.assertEqual(out[2]['order_ambiguity'], 'stop_vs_target|target_order')
        self.assertEqual(out[2]['events'], 'stop')

    def test_trace_fill_case(self):
        rows = [self.row(),
                self.row(21, open='100.4', high='103', low='100', close='102',
                         prior_high='', prior_low='', prior_atr='')]
        out = trace_rows(rows)
        self.assertEqual(out[1]['order_ambiguity'], 'fill_vs_target')
        self.assertEqual(out[1]['targets_hit'], '')

    def test_sample_files_cli(self):
        for name, expected in (('sample_order_ambiguity.csv', ['', '', 'stop_vs_target|target_order']),
                               ('sample_order_ambiguity_fill.csv', ['', 'fill_vs_target', 'target_order'])):
            p = subprocess.run([sys.executable, '-m', 'reference.engine', name],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            rows = list(csv.DictReader(io.StringIO(p.stdout)))
            self.assertEqual([r['order_ambiguity'] for r in rows], expected, name)

    def test_comparator_accepts_new_field(self):
        from reference.compare_trace import compare_detailed
        import tempfile, os
        p = subprocess.run([sys.executable, '-m', 'reference.engine', 'sample_order_ambiguity.csv'],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        with tempfile.TemporaryDirectory() as d:
            trace = Path(d) / 'trace.csv'
            obs = Path(d) / 'obs.csv'
            trace.write_text(p.stdout)
            obs.write_text('index,field,value\n22,order_ambiguity,stop_vs_target|target_order\n')
            count, differences, _, _ = compare_detailed(str(trace), str(obs))
            self.assertEqual((count, differences), (1, []))
            obs.write_text('index,field,value\n22,order_ambiguity,stop_vs_target\n')
            _, differences, _, _ = compare_detailed(str(trace), str(obs))
            self.assertEqual(len(differences), 1)


if __name__ == '__main__':
    unittest.main()
