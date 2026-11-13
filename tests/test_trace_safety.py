import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from reference.engine import Bar, Config, Engine

ROOT=Path(__file__).resolve().parents[1]
class TraceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.dir=Path(self.tmp.name)
        self.input=self.dir/'bars.csv';self.input.write_bytes((ROOT/'sample_trace.csv').read_bytes());self.output=self.dir/'trace.csv'
    def run_trace(self,*args,optimized=False):
        return subprocess.run([sys.executable,*(['-O'] if optimized else []),'-m','reference.engine',str(self.input),*map(str,args)],capture_output=True,text=True)
    def test_new_output_created(self):
        p=self.run_trace('--output',self.output);self.assertEqual(p.returncode,0,p.stderr);self.assertIn('armed_long',self.output.read_text())
    def test_existing_output_not_clobbered(self):
        self.output.write_text('existing evidence');p=self.run_trace('--output',self.output);self.assertEqual(p.returncode,2);self.assertIn('already exists',p.stderr);self.assertEqual(self.output.read_text(),'existing evidence')
    def test_explicit_force_replaces_existing_output(self):
        self.output.write_text('old');p=self.run_trace('--output',self.output,'--force');self.assertEqual(p.returncode,0,p.stderr);self.assertIn('armed_long',self.output.read_text())
    def test_input_cannot_be_forced(self):
        b=self.input.read_bytes();p=self.run_trace('--output',self.input,'--force');self.assertEqual(p.returncode,2);self.assertEqual(b,self.input.read_bytes())
    def test_config_cannot_be_forced(self):
        cfg=self.dir/'config.json';cfg.write_text('{}');p=self.run_trace('--config',cfg,'--output',cfg,'--force');self.assertEqual(p.returncode,2);self.assertEqual(cfg.read_text(),'{}')
    def test_input_hardlink_refused(self):
        os.link(self.input,self.output);before=self.input.read_bytes();p=self.run_trace('--output',self.output,'--force');self.assertEqual(p.returncode,2);self.assertEqual(self.input.read_bytes(),before)
    def test_config_hardlink_refused(self):
        cfg=self.dir/'config.json';cfg.write_text('{}');os.link(cfg,self.output);p=self.run_trace('--config',cfg,'--output',self.output,'--force');self.assertEqual(p.returncode,2);self.assertEqual(cfg.read_text(),'{}')
    def test_output_symlink_refused(self):
        target=self.dir/'target';target.write_text('safe');self.output.symlink_to(target);p=self.run_trace('--output',self.output,'--force');self.assertEqual(p.returncode,2);self.assertEqual(target.read_text(),'safe')
    def test_broken_output_symlink_refused(self):
        self.output.symlink_to(self.dir/'not-there');p=self.run_trace('--output',self.output);self.assertEqual(p.returncode,2);self.assertTrue(self.output.is_symlink())
    def test_force_requires_output(self): self.assertEqual(self.run_trace('--force').returncode,2)
    def test_invalid_trace_does_not_overwrite_existing(self):
        self.output.write_text('preserve');self.input.write_text('index,day\n20,2026-01-01\n');p=self.run_trace('--output',self.output,'--force');self.assertEqual(p.returncode,2);self.assertEqual(self.output.read_text(),'preserve')
    def test_unterminated_quote_reported(self):
        self.input.write_text('index,day,open,high,low,close,prior_high,prior_low,prior_atr\n20,"2026-01-01');p=self.run_trace();self.assertEqual(p.returncode,2);self.assertIn('Trace error:',p.stderr);self.assertNotIn('Traceback',p.stderr)
    def test_invalid_utf8_reported(self):
        self.input.write_bytes(b'\xff');p=self.run_trace();self.assertEqual(p.returncode,2);self.assertIn('Trace error:',p.stderr);self.assertNotIn('Traceback',p.stderr)
    def test_optimized_python_still_rejects_bad_config(self):
        cfg=self.dir/'cfg.json';cfg.write_text('{"tick": 0}');p=self.run_trace('--config',cfg,optimized=True);self.assertEqual(p.returncode,2);self.assertIn('invalid config',p.stderr)
    def test_too_fine_tick_rejected(self):
        cfg=self.dir/'cfg.json';cfg.write_text('{"tick": 0.00000000001}');p=self.run_trace('--config',cfg);self.assertEqual(p.returncode,2)
    def test_no_temporary_files_remain(self):
        self.assertEqual(self.run_trace('--output',self.output).returncode,0);self.assertEqual(list(self.dir.glob('.retest-trace-*')),[])
    def test_output_directory_rejected(self): self.assertEqual(self.run_trace('--output',self.dir,'--force').returncode,2)

class DirectValidationTests(unittest.TestCase):
    def test_tick_precision(self):
        Config(tick=1e-10)
        for tick in (1e-11,1.00000000001,float('nan'),float('inf')):
            with self.assertRaises(ValueError):Config(tick=tick)
    def test_config_invalid_types_and_nonfinite(self):
        for kwargs in ({'expiry':1.5},{'cap':True},{'use_ema':1},{'targets':(1,2,3,float('inf'))},{'body_mult':float('nan')}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):Config(**kwargs)
    def test_step_rejects_invalid_ohlc(self):
        with self.assertRaises(ValueError):Engine().step(Bar(1,'2026-01-01',10,9,8,10))

if __name__=='__main__':unittest.main()
