import csv,subprocess,sys,tempfile,unittest
from pathlib import Path
from reference.preflight import inspect,validate_expected_seconds
ROOT=Path(__file__).resolve().parents[1]
FIELDS=['index','day','open','high','low','close','prior_high','prior_low','prior_atr','timestamp','in_session','confirmed']
class CadenceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.d=Path(self.temp.name);self.path=self.d/'bars.csv';self.out=self.d/'report.html'
 def rows(self,*times):
  with self.path.open('w',newline='',encoding='utf8') as f:
   w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
   for i,t in enumerate(times):w.writerow(dict(index=i,day='2026-01-01',open=100,high=101,low=99,close=100,prior_high=105,prior_low=95,prior_atr=2,timestamp=t,in_session='true',confirmed='true'))
 def warn(self,seconds=300):return inspect(self.path,expected_seconds=seconds)[1]
 def names(self):return [x[0] for x in self.warn()]
 def command(self,module,*args):return subprocess.run([sys.executable,'-m',module,*map(str,args)],cwd=ROOT,capture_output=True,text=True)
 def test_exact_interval_is_not_warned(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:05:00Z');self.assertEqual(self.warn(),[])
 def test_long_gap_flags_later_bar(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:15:00Z');w=self.warn();self.assertEqual([i for n,i in w if 'longer than expected' in n],[[1]])
 def test_short_interval_flags_later_bar(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:04:59Z');self.assertTrue(any('shorter than expected' in n for n in self.names()))
 def test_fractional_seconds_checked(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:04:59.999999Z');self.assertTrue(any('shorter than expected' in n for n in self.names()))
 def test_different_offsets_compared_as_instants(self):
  self.rows('2026-01-01T10:00:00+00:00','2026-01-01T11:05:00+01:00');self.assertEqual(self.warn(),[])
 def test_dst_offset_change(self):
  self.rows('2026-01-01T01:55:00-05:00','2026-01-01T03:00:00-04:00');self.assertEqual(self.warn(),[])
 def test_blank_makes_both_pairs_unchecked(self):
  self.rows('2026-01-01T10:00:00Z','','2026-01-01T10:10:00Z');w=self.warn();self.assertEqual([i for n,i in w if 'interval not checked' in n],[[1,2]]);self.assertFalse(any('longer than expected' in n for n,i in w))
 def test_naive_makes_pair_unchecked(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:05:00');self.assertTrue(any('interval not checked' in n for n in self.names()))
 def test_duplicate_is_existing_warning_not_short(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:00:00Z');n=self.names();self.assertTrue(any('repeat the same instant' in x for x in n));self.assertFalse(any('shorter than expected' in x for x in n))
 def test_reverse_is_existing_warning_not_short(self):
  self.rows('2026-01-01T10:05:00Z','2026-01-01T10:00:00Z');n=self.names();self.assertTrue(any('go backwards' in x for x in n));self.assertFalse(any('shorter than expected' in x for x in n))
 def test_no_expected_means_no_cadence_warning(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:15:00Z');self.assertFalse(any('expected' in x[0] for x in inspect(self.path)[1]))
 def test_single_bar_no_adjacent_pairs(self):
  self.rows('2026-01-01T10:00:00Z');self.assertTrue(any('fewer than two bars' in n for n in self.names()))
 def test_multiple_categories_and_indexes(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:02:00Z','2026-01-01T10:15:00Z','');w=self.warn();self.assertEqual([i for n,i in w if 'shorter than expected' in n],[[1]]);self.assertEqual([i for n,i in w if 'longer than expected' in n],[[2]]);self.assertEqual([i for n,i in w if 'interval not checked' in n],[[3]])
 def test_invalid_bounds_and_types(self):
  for x in (0,-1,31536001,True,1.5,'300'):
   with self.subTest(x=x),self.assertRaises(ValueError):validate_expected_seconds(x)
 def test_inclusive_bounds(self):
  self.assertEqual(validate_expected_seconds(1),1);self.assertEqual(validate_expected_seconds(31536000),31536000);self.assertIsNone(validate_expected_seconds(None))
 def test_preflight_strict_gap(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:15:00Z');p=self.command('reference.preflight',self.path,'--expected-seconds',300,'--strict');self.assertEqual(p.returncode,1,p.stderr);self.assertIn('market closures and breaks may be normal',p.stdout)
 def test_preflight_non_strict_gap(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:15:00Z');p=self.command('reference.preflight',self.path,'--expected-seconds',300);self.assertEqual(p.returncode,0);self.assertIn('longer than expected',p.stdout)
 def test_preflight_invalid_interval(self):
  self.rows('2026-01-01T10:00:00Z');p=self.command('reference.preflight',self.path,'--expected-seconds',0);self.assertEqual(p.returncode,2);self.assertIn('expected seconds',p.stderr);self.assertNotIn('Traceback',p.stderr)
 def test_audit_requested_gap_and_strict(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:15:00Z');p=self.command('reference.audit_report','--bars',self.path,'--output',self.out,'--expected-seconds',300,'--strict');self.assertEqual(p.returncode,1,p.stderr);s=self.out.read_text();self.assertIn('Advisory cadence: 300 seconds',s);self.assertIn('longer than expected',s);self.assertIn('market closures',s.lower())
 def test_audit_not_requested(self):
  self.rows('2026-01-01T10:00:00Z');p=self.command('reference.audit_report','--bars',self.path,'--output',self.out);self.assertEqual(p.returncode,0,p.stderr);self.assertIn('Cadence check: not requested',self.out.read_text())
 def test_audit_invalid_no_output(self):
  self.rows('2026-01-01T10:00:00Z');p=self.command('reference.audit_report','--bars',self.path,'--output',self.out,'--expected-seconds',31536001);self.assertEqual(p.returncode,2);self.assertFalse(self.out.exists())
 def test_inputs_unchanged(self):
  self.rows('2026-01-01T10:00:00Z','2026-01-01T10:15:00Z');b=self.path.read_bytes();self.warn();self.assertEqual(b,self.path.read_bytes())
 def test_audit_bundled_workflow(self):
  p=self.command('reference.audit_report','--bars',ROOT/'sample_trace.csv','--bundle',ROOT/'sample_evidence_bundle.json','--expected-seconds',300,'--output',self.out);self.assertEqual(p.returncode,1,p.stderr);s=self.out.read_text();self.assertIn('Advisory cadence: 300 seconds',s);self.assertIn('Evidence bundle:',s)
if __name__=='__main__':unittest.main()
