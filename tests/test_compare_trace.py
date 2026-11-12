import csv
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from reference.compare_trace import FIELDS, compare

class CompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name); self.trace = self.d/'trace.csv'; self.obs = self.d/'obs.csv'
        row = dict.fromkeys(('index', *FIELDS), ''); row.update(index='20', state='armed', events='armed_long', entry='100.0')
        self.write(self.trace, ('index', *FIELDS), [row]); self.write_obs([('20','entry','100.00')])
    def write(self, path, fields, rows):
        with path.open('w', newline='', encoding='utf8') as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    def write_obs(self, rows):
        self.write(self.obs, ('index','field','value'), [dict(zip(('index','field','value'),r)) for r in rows])
    def test_decimal_equivalence(self): self.assertEqual(compare(self.trace,self.obs), (1, []))
    def test_mismatch(self):
        self.write_obs([('20','entry','100.01')]); self.assertEqual(compare(self.trace,self.obs)[1][0],(20,'entry','100.0','100.01'))
    def test_explicit_blank_matches_blank(self):
        self.write_obs([('20','cancel_reason','')]); self.assertEqual(compare(self.trace,self.obs),(1,[]))
    def test_blank_does_not_match_number(self):
        self.write_obs([('20','entry','')]); self.assertEqual(len(compare(self.trace,self.obs)[1]),1)
    def test_unknown_index(self):
        self.write_obs([('21','entry','100')]); self.assertRaises(ValueError,compare,self.trace,self.obs)
    def test_unknown_field(self):
        self.write_obs([('20','price','100')]); self.assertRaises(ValueError,compare,self.trace,self.obs)
    def test_duplicate_pair(self):
        self.write_obs([('20','entry','100'),('020','entry','100')]); self.assertRaises(ValueError,compare,self.trace,self.obs)
    def test_duplicate_trace_index(self):
        with self.trace.open('a') as f: f.write('20'+','*len(FIELDS)+'\n')
        self.assertRaises(ValueError,compare,self.trace,self.obs)
    def test_nonfinite_rejected(self):
        self.write_obs([('20','entry','NaN')]); self.assertRaises(ValueError,compare,self.trace,self.obs)
    def test_text_order_matters(self):
        self.write_obs([('20','events','armed_short')]); self.assertEqual(len(compare(self.trace,self.obs)[1]),1)
    def test_missing_or_extra_header_rejected(self):
        self.obs.write_text('index,field,value,extra\n20,entry,100,x\n'); self.assertRaises(ValueError,compare,self.trace,self.obs)
    def test_empty_observations_rejected(self):
        self.write_obs([]); self.assertRaises(ValueError,compare,self.trace,self.obs)
    def test_malformed_row_rejected(self):
        self.obs.write_text('index,field,value\n20,entry\n'); self.assertRaises(ValueError,compare,self.trace,self.obs)
    def test_unterminated_quote_rejected(self):
        self.obs.write_text('index,field,value\n20,events,"armed_long\n'); self.assertRaises(csv.Error,compare,self.trace,self.obs)
    def test_invalid_utf8_command_error(self):
        self.obs.write_bytes(b'index,field,value\n20,entry,\xff\n')
        cmd=[sys.executable,'-m','reference.compare_trace',str(self.trace),str(self.obs)]
        result=subprocess.run(cmd,capture_output=True,text=True); self.assertEqual(result.returncode,2); self.assertIn('Comparison error:',result.stderr)
    def test_command_exit_codes_and_read_only(self):
        before=(self.trace.read_bytes(),self.obs.read_bytes())
        cmd=[sys.executable,'-m','reference.compare_trace',str(self.trace),str(self.obs)]
        ok=subprocess.run(cmd,capture_output=True,text=True); self.assertEqual(ok.returncode,0); self.assertIn('Unrecorded cells were not checked',ok.stdout)
        self.assertEqual(before,(self.trace.read_bytes(),self.obs.read_bytes()))
        self.write_obs([('20','entry','101')]); self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,1)
        self.write_obs([('20','bogus','101')]); self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,2)
    def test_synthetic_sample(self):
        root=Path(__file__).resolve().parents[1]; t=self.d/'sample.csv'
        p=subprocess.run([sys.executable,'-m','reference.engine',str(root/'sample_trace.csv'),'--output',str(t)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr); self.assertEqual(compare(t,root/'sample_observations.csv'),(5,[]))

    def test_short_synthetic_sample(self):
        root=Path(__file__).resolve().parents[1]; t=self.d/'short.csv'
        p=subprocess.run([sys.executable,'-m','reference.engine',str(root/'sample_short_trace.csv'),'--output',str(t)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr); self.assertEqual(compare(t,root/'sample_short_observations.csv'),(5,[]))

if __name__ == '__main__': unittest.main()
