import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reference.alerts import validate as validate_alert
from reference.engine import Bar, Config, diagnose, trace_rows
from reference.parity import compare as parity_compare, parse_pine_inputs

ROOT = Path(__file__).resolve().parents[1]


def bar(**kw):
    d = dict(open=99.5, high=102, low=99, close=101.8)
    d.update(kw)
    return Bar(20, '2026-01-01', d['open'], d['high'], d['low'], d['close'])


class DiagnoseTests(unittest.TestCase):
    def test_long_passes(self):
        setup, reason = diagnose(bar(), 100, 95, 2, Config())
        self.assertIsNotNone(setup)
        self.assertIsNone(reason)

    def test_short_passes(self):
        setup, reason = diagnose(Bar(20, 'd', 100.5, 101, 98, 98.2), 105, 100, 2, Config())
        self.assertEqual(setup.direction, -1)
        self.assertIsNone(reason)

    def test_no_breakout(self):
        self.assertEqual(diagnose(Bar(20, 'd', 98, 100, 97, 99.8), 100, 95, 2, Config())[1], 'no_breakout')

    def test_direction_disabled(self):
        self.assertEqual(diagnose(bar(), 100, 95, 2, Config(longs=False))[1], 'direction_disabled')

    def test_min_break(self):
        self.assertEqual(diagnose(bar(), 100, 95, 2, Config(min_break_atr=1))[1], 'min_break')

    def test_close_direction(self):
        # Breaks the prior high (close 101 > 100) but closes below its open.
        self.assertEqual(diagnose(Bar(20, 'd', 102, 102, 99, 101), 100, 95, 2, Config())[1], 'close_direction')

    def test_weak_body(self):
        self.assertEqual(diagnose(bar(open=101.5), 100, 95, 2, Config())[1], 'weak_body')

    def test_close_edge(self):
        self.assertEqual(diagnose(bar(high=105), 100, 95, 2, Config())[1], 'close_edge')

    def test_ema_missing_and_wrong_side(self):
        c = Config(use_ema=True)
        self.assertEqual(diagnose(bar(), 100, 95, 2, c)[1], 'ema')
        self.assertEqual(diagnose(bar(), 100, 95, 2, c, ema=102)[1], 'ema')
        self.assertIsNone(diagnose(bar(), 100, 95, 2, c, ema=100)[1])

    def test_vwap_missing_and_wrong_side(self):
        c = Config(use_vwap=True)
        self.assertEqual(diagnose(bar(), 100, 95, 2, c)[1], 'vwap')
        self.assertEqual(diagnose(bar(), 100, 95, 2, c, vwap=102)[1], 'vwap')

    def test_volume_missing_and_low(self):
        c = Config(use_volume=True, vol_mult=1.5)
        self.assertEqual(diagnose(bar(), 100, 95, 2, c)[1], 'volume')
        self.assertEqual(diagnose(bar(), 100, 95, 2, c, volume=100, prior_volume_avg=100)[1], 'volume')
        self.assertIsNone(diagnose(bar(), 100, 95, 2, c, volume=150, prior_volume_avg=100)[1])

    def test_zero_atr(self):
        self.assertEqual(diagnose(bar(), 100, 95, 0, Config())[1], 'zero_atr')

    def test_invalid_bar(self):
        self.assertEqual(diagnose(Bar(20, 'd', 100, 100, 100, 100), 100, 95, 2, Config())[1], 'invalid_bar')
        self.assertEqual(diagnose(Bar(20, 'd', 99.5, 102, 99, 101.8, confirmed=False), 100, 95, 2, Config())[1], 'invalid_bar')

    def test_risk_out_of_range(self):
        # Breakout bar whose stop is too close: tiny risk below min_risk.
        self.assertEqual(diagnose(Bar(20, 'd', 99.5, 102, 99.9, 101.8), 100, 95, 2, Config())[1], 'risk_out_of_range')

    def test_targets_collapsed(self):
        self.assertEqual(diagnose(bar(), 100, 95, 2, Config(tick=1, targets=(.1, .2, .3, .4)))[1], 'targets_collapsed')

    def test_first_failure_order_geometry_before_filter(self):
        # Weak body AND missing EMA: geometry is reported first.
        self.assertEqual(diagnose(bar(open=101.5), 100, 95, 2, Config(use_ema=True))[1], 'weak_body')

    def test_no_breakout_before_filter(self):
        self.assertEqual(diagnose(Bar(20, 'd', 98, 100, 97, 99.8), 100, 95, 2, Config(use_ema=True))[1], 'no_breakout')


class TraceRejectTests(unittest.TestCase):
    def test_sample_reject_csv(self):
        p = subprocess.run([sys.executable, '-m', 'reference.engine', 'sample_reject.csv'],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        rows = list(csv.DictReader(io.StringIO(p.stdout)))
        self.assertEqual([r['reject_reason'] for r in rows],
                         ['weak_body', 'close_edge', 'no_breakout', ''])
        self.assertEqual(rows[-1]['events'], 'armed_long')

    def test_warmup_reason(self):
        rows = [{'index': '20', 'day': '2026-01-01', 'open': '99.5', 'high': '102', 'low': '99',
                 'close': '101.8', 'prior_high': '', 'prior_low': '', 'prior_atr': ''}]
        self.assertEqual(trace_rows(rows)[0]['reject_reason'], 'warmup')

    def test_no_reject_reason_on_armed_or_active_bars(self):
        # v0.23 recorded a candidate diagnosis regardless of state, so a
        # bar could show both modeled_fill and reject_reason warmup.
        # v0.24 records a reason only on bars that started idle: arming
        # is only attempted from idle, so armed/active bars carry none.
        p = subprocess.run([sys.executable, '-m', 'reference.engine', 'sample_trace.csv'],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        rows = list(csv.DictReader(io.StringIO(p.stdout)))
        self.assertEqual([r['reject_reason'] for r in rows], ['', '', ''])
        self.assertEqual([r['events'] for r in rows],
                         ['armed_long', 'modeled_fill', 'target_1|target_2|target_3|target_4'])

    def test_comparator_accepts_reject_reason(self):
        from reference.compare_trace import compare_detailed
        p = subprocess.run([sys.executable, '-m', 'reference.engine', 'sample_reject.csv'],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        with tempfile.TemporaryDirectory() as d:
            trace = Path(d) / 'trace.csv'
            obs = Path(d) / 'obs.csv'
            trace.write_text(p.stdout)
            obs.write_text('index,field,value\n20,reject_reason,weak_body\n')
            count, differences, _, _ = compare_detailed(str(trace), str(obs))
            self.assertEqual((count, differences), (1, []))


class ParityTests(unittest.TestCase):
    def test_defaults_agree(self):
        differences, pine_only, _ = parity_compare(str(ROOT / 'retest_lab.pine'), Config())
        self.assertEqual(differences, [])
        self.assertIn('lookback', pine_only)

    def test_changed_config_is_reported(self):
        differences, _, _ = parity_compare(str(ROOT / 'retest_lab.pine'), Config(tick=0.05, expiry=3))
        # tick is Pine mintick, not an input, so only expiry differs.
        self.assertEqual(differences, [('expiry', 10, 3)])

    def test_cli_exit_codes(self):
        p = subprocess.run([sys.executable, '-m', 'reference.parity', '--pine', 'retest_lab.pine'],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('agree on every shared field', p.stdout)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'expiry': 3}, f)
            path = f.name
        try:
            p = subprocess.run([sys.executable, '-m', 'reference.parity', '--pine', 'retest_lab.pine',
                                '--config', path], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn('expiry', p.stdout)
        finally:
            Path(path).unlink()

    def test_missing_pine_file_is_error(self):
        p = subprocess.run([sys.executable, '-m', 'reference.parity', '--pine', 'nope.pine'],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


class AlertTests(unittest.TestCase):
    def valid(self):
        return {"schema": "retest_lab.v3", "symbol": "NASDAQ:AAPL", "timeframe": "5",
                "bar_close_ms": 1766452800000, "direction": 1, "events": ["armed_long"],
                "cancel_reason": None, "entry": 100.0, "stop": 98.8,
                "t1": 100.72, "t2": 101.2, "t3": 101.8, "t4": 102.4}

    def test_valid_alert(self):
        self.assertEqual(validate_alert(self.valid()), [])

    def test_sample_alert_cli(self):
        p = subprocess.run([sys.executable, '-m', 'reference.alerts', 'sample_alert.json'],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_wrong_schema(self):
        payload = self.valid()
        payload['schema'] = 'retest_lab.v2'
        self.assertTrue(any('schema' in x for x in validate_alert(payload)))

    def test_unknown_event(self):
        payload = self.valid()
        payload['events'] = ['made_up']
        self.assertTrue(any('unknown events' in x for x in validate_alert(payload)))

    def test_cancel_without_reason(self):
        payload = self.valid()
        payload['events'] = ['cancelled']
        self.assertTrue(any('cancel_reason' in x for x in validate_alert(payload)))

    def test_reason_without_cancel(self):
        payload = self.valid()
        payload['cancel_reason'] = 'expired'
        self.assertTrue(any('cancel_reason' in x for x in validate_alert(payload)))

    def test_bad_direction_and_prices(self):
        payload = self.valid()
        payload['direction'] = 0
        payload['entry'] = '100'
        problems = validate_alert(payload)
        self.assertTrue(any('direction' in x for x in problems))
        self.assertTrue(any('entry' in x for x in problems))

    def test_bad_file_is_error(self):
        p = subprocess.run([sys.executable, '-m', 'reference.alerts', 'nope.json'],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


if __name__ == '__main__':
    unittest.main()
