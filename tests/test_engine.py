import unittest
from reference.engine import Bar, Config, Setup, Engine, detect

def b(i, low=101, high=102, day='2026-01-01', **kw):
    return Bar(i, day, kw.pop('open', (low+high)/2), high, low,
               kw.pop('close', (low+high)/2), **kw)
L = Setup(1, 100, 98, (101.2, 102, 103, 104))
S = Setup(-1, 100, 102, (98.8, 98, 97, 96))

class LifecycleTests(unittest.TestCase):
    def arm(self, cfg=None, setup=L):
        e = Engine(cfg or Config())
        self.assertTrue(e.step(b(0), setup)[0].startswith('armed_'))
        return e
    def test_no_breakout_bar_fill(self):
        e = self.arm(); self.assertEqual(e.state, 'armed'); self.assertEqual(e.fills_today, 0)
    def test_exact_touch_fills(self):
        e = self.arm(); self.assertEqual(e.step(b(1, 100, 100.5)), ['modeled_fill'])
    def test_near_miss_does_not_fill(self):
        e = self.arm(); self.assertEqual(e.step(b(1, 100.01, 100.5)), []); self.assertEqual(e.state, 'armed')
    def test_last_valid_bar_fills(self):
        e = self.arm(Config(expiry=2)); self.assertEqual(e.step(b(2, 100, 100.5)), ['modeled_fill'])
    def test_expired_touch_cancels(self):
        e = self.arm(Config(expiry=2)); self.assertEqual(e.step(b(3, 100, 100.5)), ['cancelled'])
    def test_pending_invalidation_beats_fill(self):
        e = self.arm(); self.assertEqual(e.step(b(1, 97, 101)), ['cancelled']); self.assertEqual(e.fills_today, 0)
    def test_active_stop_beats_all_targets(self):
        e = self.arm(); e.step(b(1, 100, 100.5)); self.assertEqual(e.step(b(2, 97, 105)), ['stop'])
    def test_multiple_targets_once(self):
        e = self.arm(); self.assertEqual(e.step(b(1, 100, 103.5)), ['modeled_fill'])
        self.assertEqual(e.step(b(2, 100, 103.5)), ['target_1','target_2','target_3'])
        self.assertEqual(e.step(b(3, 100, 103.5)), [])
    def test_final_target_closes(self):
        e = self.arm(); e.step(b(1, 100, 104)); self.assertEqual(e.state, 'active'); e.step(b(2, 100, 104)); self.assertEqual(e.state, 'idle')
    def test_short_mirrors_long(self):
        e = self.arm(setup=S); self.assertEqual(e.step(b(1, 97, 100)), ['modeled_fill']); self.assertEqual(e.step(b(2, 97, 100)), ['target_1','target_2','target_3'])
    def test_cooldown_blocks_full_bars(self):
        e = self.arm(Config(cooldown=2)); e.step(b(1, 97, 100)); self.assertEqual(e.step(b(3), L), [])
        self.assertEqual(e.step(b(4), L), ['armed_long'])
    def test_no_rearm_on_termination_bar(self):
        e = self.arm(Config(cooldown=0)); self.assertEqual(e.step(b(1, 97, 101), L), ['cancelled'])
    def test_cap_blocks_new_setup(self):
        e = self.arm(Config(cap=1,cooldown=0)); e.step(b(1,100,104)); e.step(b(2,100,104)); self.assertEqual(e.step(b(3), L), [])
    def test_day_resets_cap(self):
        e = self.arm(Config(cap=1,cooldown=0)); e.step(b(1,100,104)); e.step(b(2,100,104))
        self.assertEqual(e.step(b(3,day='2026-01-02'), L), ['armed_long']); self.assertEqual(e.fills_today,0)
    def test_day_cancels_pending(self):
        e = self.arm(); self.assertEqual(e.step(b(1,day='2026-01-02')), ['cancelled'])
    def test_session_cancels_pending(self):
        e = self.arm(); self.assertEqual(e.step(b(1,in_session=False)), ['cancelled'])
    def test_active_survives_session_end(self):
        e = self.arm(); e.step(b(1,100,100.5)); self.assertEqual(e.step(b(2,100,100.5,in_session=False)), []); self.assertEqual(e.state,'active')
    def test_unconfirmed_bar_no_state_change(self):
        e = Engine(); self.assertEqual(e.step(b(0,confirmed=False), L), []); self.assertIsNone(e.day)
    def test_gap_below_entry_not_a_fill(self):
        e = self.arm(); self.assertEqual(e.step(b(1,98.5,99.5)), []); self.assertEqual(e.state,'armed')
    def test_outside_session_no_arm(self):
        self.assertEqual(Engine().step(b(0,in_session=False),L), [])

class DetectionTests(unittest.TestCase):
    def test_long_geometry(self):
        s = detect(Bar(20,'d',99.5,102,99,101.8),100,95,2,Config())
        self.assertEqual(s, Setup(1,100,98.8,(100.72,101.2,101.8,102.4)))
    def test_short_geometry(self):
        s = detect(Bar(20,'d',100.5,101,98,98.2),105,100,2,Config())
        self.assertEqual(s, Setup(-1,100,101.2,(99.28,98.8,98.2,97.6)))
    def test_weak_body_rejected(self):
        self.assertIsNone(detect(Bar(20,'d',101.5,102,99,101.8),100,95,2,Config()))
    def test_close_edge_rejected(self):
        self.assertIsNone(detect(Bar(20,'d',99,105,98,101.8),100,95,2,Config()))
    def test_no_break_rejected(self):
        self.assertIsNone(detect(Bar(20,'d',98,100,97,99.8),100,95,2,Config()))
    def test_zero_atr_rejected(self):
        self.assertIsNone(detect(Bar(20,'d',99.5,102,99,101.8),100,95,0,Config()))
    def test_wrong_side_stop_rejected(self):
        self.assertIsNone(detect(Bar(20,'d',101,104,100.5,103.8),100,95,2,Config()))
    def test_targets_must_be_increasing(self):
        with self.assertRaises(ValueError): Config(targets=(1,.6,1.5,2))
    def test_tick_collapsed_targets_rejected(self):
        self.assertIsNone(detect(Bar(20,'d',99.5,102,99,101.8),100,95,2,Config(tick=1, targets=(.1,.2,.3,.4))))
    def test_direction_disabled(self):
        self.assertIsNone(detect(Bar(20,'d',99.5,102,99,101.8),100,95,2,Config(longs=False)))


class FilterTests(unittest.TestCase):
    bar = Bar(20,'d',99.5,102,99,101.8)
    def test_ema_filter_pass_and_fail(self):
        c = Config(use_ema=True)
        self.assertIsNotNone(detect(self.bar,100,95,2,c,ema=100))
        self.assertIsNone(detect(self.bar,100,95,2,c,ema=102))
        self.assertIsNone(detect(self.bar,100,95,2,c))
    def test_volume_filter_missing_and_threshold(self):
        c = Config(use_volume=True,vol_mult=1.5)
        self.assertIsNone(detect(self.bar,100,95,2,c))
        self.assertIsNone(detect(self.bar,100,95,2,c,volume=149,prior_volume_avg=100))
        self.assertIsNotNone(detect(self.bar,100,95,2,c,volume=150,prior_volume_avg=100))
    def test_filters_off_do_not_require_inputs(self):
        self.assertIsNotNone(detect(self.bar,100,95,2,Config()))
    def test_fill_bar_target_is_deferred(self):
        e=Engine(); e.step(b(0),L)
        self.assertEqual(e.step(b(1,100,105)),['modeled_fill'])
        self.assertEqual(e.state,'active'); self.assertEqual(e.hit,set())
    def test_next_bar_stop_wins_after_ambiguous_fill(self):
        e=Engine(); e.step(b(0),L); e.step(b(1,100,105))
        self.assertEqual(e.step(b(2,97,105)),['stop'])


class V3FeatureTests(unittest.TestCase):
    long_bar = Bar(20,'d',99.5,102,99,101.8)
    short_bar = Bar(20,'d',100.5,101,98,98.2)
    def test_min_break_long_pass(self):
        self.assertIsNotNone(detect(self.long_bar,100,95,2,Config(min_break_atr=.8)))
    def test_min_break_long_fail(self):
        self.assertIsNone(detect(self.long_bar,100,95,2,Config(min_break_atr=1)))
    def test_min_break_short_pass(self):
        self.assertIsNotNone(detect(self.short_bar,105,100,2,Config(min_break_atr=.8)))
    def test_min_break_short_fail(self):
        self.assertIsNone(detect(self.short_bar,105,100,2,Config(min_break_atr=1)))
    def test_min_break_equality(self):
        self.assertIsNotNone(detect(Bar(20,'d',99.5,102,99,102),100,95,2,Config(min_break_atr=1)))
    def test_negative_break_rejected(self):
        with self.assertRaises(ValueError): Config(min_break_atr=-1)
    def test_confirm_long_waits_and_then_fills(self):
        e=Engine(Config(confirm_retest=True));e.step(b(0),L)
        self.assertEqual(e.step(b(1,99,101,close=99.5)),[])
        self.assertEqual(e.state,'armed');self.assertEqual(e.step(b(2,99,101,close=100)),['modeled_fill'])
    def test_confirm_short_waits_and_then_fills(self):
        e=Engine(Config(confirm_retest=True));e.step(b(0),S)
        self.assertEqual(e.step(b(1,99,101,close=100.5)),[])
        self.assertEqual(e.step(b(2,99,101,close=100)),['modeled_fill'])
    def test_stop_before_confirmation(self):
        e=Engine(Config(confirm_retest=True));e.step(b(0),L)
        self.assertEqual(e.step(b(1,97,101,close=100.5)),['cancelled'])
        self.assertEqual(e.last_cancel_reason,'stop_before_fill')
    def test_expiry_reason(self):
        e=Engine(Config(expiry=1));e.step(b(0),L);e.step(b(2))
        self.assertEqual(e.last_cancel_reason,'expired')
    def test_session_reason(self):
        e=Engine();e.step(b(0),L);e.step(b(1,in_session=False))
        self.assertEqual(e.last_cancel_reason,'outside_session')
    def test_day_precedes_other_cancellations(self):
        e=Engine(Config(expiry=1));e.step(b(0),L);e.step(b(3,97,101,day='2026-01-02',in_session=False))
        self.assertEqual(e.last_cancel_reason,'day_rollover')
    def test_session_precedes_expiry_and_stop(self):
        e=Engine(Config(expiry=1));e.step(b(0),L);e.step(b(3,97,101,in_session=False))
        self.assertEqual(e.last_cancel_reason,'outside_session')
    def test_expiry_precedes_stop(self):
        e=Engine(Config(expiry=1));e.step(b(0),L);e.step(b(2,97,101))
        self.assertEqual(e.last_cancel_reason,'expired')

class VWAPTests(unittest.TestCase):
    def test_long_pass_fail_equal_and_missing(self):
        bar=Bar(20,'d',99.5,102,99,101.8); c=Config(use_vwap=True)
        self.assertIsNotNone(detect(bar,100,95,2,c,vwap=100))
        for v in (102,101.8,None): self.assertIsNone(detect(bar,100,95,2,c,vwap=v))
    def test_short_pass_fail_equal_and_missing(self):
        bar=Bar(20,'d',100.5,101,98,98.2); c=Config(use_vwap=True)
        self.assertIsNotNone(detect(bar,105,100,2,c,vwap=100))
        for v in (98,98.2,None): self.assertIsNone(detect(bar,105,100,2,c,vwap=v))
    def test_vwap_off_needs_no_input(self):
        self.assertIsNotNone(detect(Bar(20,'d',99.5,102,99,101.8),100,95,2,Config()))



class DiagnosticTraceTests(unittest.TestCase):
    def row(self, i=20, **kwargs):
        d={'index':str(i),'day':'2026-01-01','open':'99.5','high':'102','low':'99','close':'101.8','prior_high':'100','prior_low':'95','prior_atr':'2'}
        d.update(kwargs); return d
    def test_hand_checked_long_lifecycle(self):
        from reference.engine import trace_rows
        rows=[self.row(),self.row(21,open='100.4',high='100.5',low='100',close='100.2',prior_high='',prior_low='',prior_atr=''),self.row(22,open='100.5',high='102.5',low='100',close='102.4',prior_high='',prior_low='',prior_atr='')]
        out=trace_rows(rows);self.assertEqual([x['events'] for x in out],['armed_long','modeled_fill','target_1|target_2|target_3|target_4']);self.assertEqual([x['state'] for x in out],['armed','active','idle']);self.assertEqual(out[-1]['fills_today'],1)
    def test_short_lifecycle(self):
        from reference.engine import trace_rows
        r=[self.row(open='100.5',high='101',low='98',close='98.2',prior_high='105',prior_low='100'),self.row(21,open='99.5',high='100',low='99',close='99.3',prior_high='',prior_low='',prior_atr='')]
        out=trace_rows(r);self.assertEqual([x['events'] for x in out],['armed_short','modeled_fill']);self.assertEqual(out[1]['direction'],-1)
    def test_cancel_reason_on_event_only(self):
        from reference.engine import trace_rows
        r=[self.row(),self.row(21,in_session='false',prior_high='',prior_low='',prior_atr=''),self.row(22,prior_high='',prior_low='',prior_atr='')]
        out=trace_rows(r);self.assertEqual(out[1]['cancel_reason'],'outside_session');self.assertEqual(out[2]['cancel_reason'],'')
    def test_fill_bar_targets_deferred(self):
        from reference.engine import trace_rows
        r=[self.row(),self.row(21,open='101',high='105',low='100',close='104',prior_high='',prior_low='',prior_atr='')]
        out=trace_rows(r);self.assertEqual(out[1]['events'],'modeled_fill');self.assertEqual(out[1]['targets_hit'],'')
    def test_missing_inputs_warmup(self):
        from reference.engine import trace_rows
        self.assertEqual(trace_rows([self.row(prior_high='',prior_low='',prior_atr='')])[0]['state'],'idle')
    def test_partial_inputs_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'all be present'): trace_rows([self.row(prior_atr='')])
    def test_gapped_indexes_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'consecutive'): trace_rows([self.row(),self.row(22)])
    def test_duplicate_indexes_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'consecutive'): trace_rows([self.row(),self.row()])
    def test_negative_index_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'nonnegative integer'): trace_rows([self.row(-1)])
    def test_bad_day_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'YYYY-MM-DD'): trace_rows([self.row(day='2026-02-30')])
    def test_backwards_day_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'nondecreasing'): trace_rows([self.row(day='2026-01-02'),self.row(21)])
    def test_bad_ohlc_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'invalid OHLC'): trace_rows([self.row(high='99')])
    def test_nan_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'finite'): trace_rows([self.row(high='nan')])
    def test_bad_boolean_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'true/false'): trace_rows([self.row(in_session='maybe')])
    def test_unconfirmed_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'confirmed bars only'): trace_rows([self.row(confirmed='false')])
    def test_negative_volume_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'volume cannot be negative'): trace_rows([self.row(volume='-1')])
    def test_bad_prior_range_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'invalid prior'): trace_rows([self.row(prior_low='101')])
    def test_vwap_missing_rejects_setup(self):
        from reference.engine import trace_rows
        self.assertEqual(trace_rows([self.row()],Config(use_vwap=True))[0]['events'],'')
    def test_confirm_retest_config(self):
        from reference.engine import trace_rows
        r=[self.row(),self.row(21,open='100.2',high='100.4',low='99.5',close='99.8',prior_high='',prior_low='',prior_atr='')]
        self.assertEqual(trace_rows(r,Config(confirm_retest=True))[1]['state'],'armed')
    def test_config_rejects_unknown_and_types(self):
        from reference.engine import load_config
        import tempfile,json,os
        for obj in ({'unknown':3},{'confirm_retest':'yes'},{'tick':float('nan')},{'expiry':2.0},{'targets':[1,2]}):
            with tempfile.NamedTemporaryFile(mode='w',delete=False) as f: json.dump(obj,f); path=f.name
            try:
                with self.assertRaises(ValueError):load_config(path)
            finally: os.unlink(path)
    def test_config_overrides(self):
        from reference.engine import load_config
        import tempfile,json,os
        with tempfile.NamedTemporaryFile(mode='w',delete=False) as f: json.dump({'expiry':3,'confirm_retest':True,'targets':[1,2,3,4]},f);path=f.name
        try:self.assertEqual(load_config(path),Config(expiry=3,confirm_retest=True,targets=(1,2,3,4)))
        finally:os.unlink(path)
    def test_bad_timestamp_rejected(self):
        from reference.engine import trace_rows
        with self.assertRaisesRegex(ValueError,'timestamp'):trace_rows([self.row(timestamp='garbage')])
    def test_expired_reason(self):
        from reference.engine import trace_rows
        r=[self.row()]+[self.row(i,open='101',high='102',low='101',close='101.5',prior_high='',prior_low='',prior_atr='') for i in range(21,23)]
        out=trace_rows(r,Config(expiry=1));self.assertEqual(out[-1]['cancel_reason'],'expired')
    def test_session_default_is_true(self):
        from reference.engine import trace_rows
        self.assertEqual(trace_rows([self.row()])[0]['events'],'armed_long')



class TraceCLITests(unittest.TestCase):
    def test_sample_file_cli(self):
        import subprocess,sys,csv,io
        p=subprocess.run([sys.executable,'-m','reference.engine','sample_trace.csv'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);rows=list(csv.DictReader(io.StringIO(p.stdout)))
        self.assertEqual([r['events'] for r in rows],['armed_long','modeled_fill','target_1|target_2|target_3|target_4'])
    def test_cli_missing_headers(self):
        import subprocess,sys,tempfile,os
        with tempfile.NamedTemporaryFile(mode='w',delete=False) as f:f.write('index,day\n1,2026-01-01\n');path=f.name
        try:
            p=subprocess.run([sys.executable,'-m','reference.engine',path],capture_output=True,text=True)
            self.assertEqual(p.returncode,2);self.assertIn('missing required',p.stderr)
        finally:os.unlink(path)
    def test_cli_refuses_input_as_output(self):
        import subprocess,sys
        p=subprocess.run([sys.executable,'-m','reference.engine','sample_trace.csv','--output','sample_trace.csv'],capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('must not overwrite',p.stderr)

if __name__ == "__main__": unittest.main()
