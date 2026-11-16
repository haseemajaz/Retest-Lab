"""Guarded overflow is a data/model error, not a trading outcome."""
import csv, io, subprocess, sys, tempfile, unittest
from pathlib import Path
from reference.engine import Bar, Config, detect, rounded, trace_rows
ROOT=Path(__file__).resolve().parents[1]
class ArithmeticSafetyTests(unittest.TestCase):
 def assert_guard(self,label,bar,hi,lo,atr,cfg=None,**kwargs):
  with self.assertRaisesRegex(ValueError,'non-finite model arithmetic: '+label):detect(bar,hi,lo,atr,cfg or Config(),**kwargs)
 def test_bar_range_overflow(self):
  self.assert_guard('bar range',Bar(0,'d',0,1e308,-1e308,1e308),0,-1,1)
 def test_long_breakout_distance_overflow(self):
  self.assert_guard('long breakout distance',Bar(0,'d',0,1e308,0,1e308),-1e308,-1e308,1)
 def test_short_breakout_distance_overflow(self):
  self.assert_guard('short breakout distance',Bar(0,'d',0,0,-1e308,-1e308),1e308,1e308,1)
 def test_volume_threshold_overflow(self):
  self.assert_guard('volume threshold',Bar(0,'d',99.5,102,99,101.8),100,95,2,Config(use_volume=True,vol_mult=2),volume=1e308,prior_volume_avg=1e308)
 def test_break_threshold_overflow(self):
  self.assert_guard('breakout threshold',Bar(0,'d',0,1e308,0,1e308),9e307,0,1e308,Config(tick=1e308,min_break_atr=2))
 def test_body_threshold_overflow(self):
  self.assert_guard('body threshold',Bar(0,'d',0,1e308,0,1e308),9e307,0,1e308,Config(tick=1e308,body_mult=2))
 def test_tick_units_overflow(self):
  with self.assertRaisesRegex(ValueError,'price / tick'):rounded(1e308,0.01)
 def test_stop_buffer_overflow(self):
  self.assert_guard('stop buffer',Bar(0,'d',0,1e308,0,1e308),9e307,0,1e308,Config(tick=1e308,stop_buffer=2))
 def test_maximum_risk_overflow(self):
  self.assert_guard('maximum risk',Bar(0,'d',0,1e308,0,1e308),8e307,0,1e308,Config(tick=1e307,stop_buffer=0))
 def test_target_distance_overflow(self):
  self.assert_guard('target distance',Bar(0,'d',7e307,1e308,6e307,1e308),8e307,0,1e307,Config(tick=1e307,stop_buffer=0,targets=(1e307,2e307,3e307,4e307)))
 def test_normal_geometry_unchanged(self):
  a=detect(Bar(20,'d',99.5,102,99,101.8),100,95,2,Config());self.assertEqual((a.entry,a.stop,a.targets),(100,98.8,(100.72,101.2,101.8,102.4)))
 def test_trace_adds_source_row(self):
  text='index,day,open,high,low,close,prior_high,prior_low,prior_atr\n0,2026-01-01,0,1e308,-1e308,1e308,0,-1,1\n'
  with self.assertRaisesRegex(ValueError,'row 2: non-finite model arithmetic: bar range'):trace_rows(csv.DictReader(io.StringIO(text)))
 def test_cli_commands_fail_without_writing_output(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);bars=root/'bars.csv';out=root/'out';bars.write_text('index,day,open,high,low,close,prior_high,prior_low,prior_atr\n0,2026-01-01,0,1e308,-1e308,1e308,0,-1,1\n')
   commands=[['reference.engine',str(bars),'--output',str(out)],['reference.preflight',str(bars)],['reference.audit_report','--bars',str(bars),'--output',str(out)]]
   for cmd in commands:
    with self.subTest(cmd=cmd[0]):
     p=subprocess.run([sys.executable,'-m',*cmd],cwd=ROOT,text=True,capture_output=True);self.assertEqual(p.returncode,2);self.assertIn('row 2: non-finite model arithmetic: bar range',p.stderr);self.assertFalse(out.exists())
 def test_force_does_not_modify_existing_output_on_failure(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);bars=root/'bars.csv';out=root/'out.csv';out.write_text('keep');bars.write_text('index,day,open,high,low,close,prior_high,prior_low,prior_atr\n0,2026-01-01,0,1e308,-1e308,1e308,0,-1,1\n');p=subprocess.run([sys.executable,'-m','reference.engine',str(bars),'--output',str(out),'--force'],cwd=ROOT,text=True,capture_output=True);self.assertEqual(p.returncode,2);self.assertEqual(out.read_text(),'keep')
 def test_optimized_mode_still_guards(self):
  code="from reference.engine import *; detect(Bar(0,'d',0,1e308,-1e308,1e308),0,-1,1,Config())"
  p=subprocess.run([sys.executable,'-O','-c',code],cwd=ROOT,text=True,capture_output=True);self.assertNotEqual(p.returncode,0);self.assertIn('non-finite model arithmetic: bar range',p.stderr)
if __name__=='__main__':unittest.main()
