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

class ChecklistTests(unittest.TestCase):
    write = CompareTests.write
    write_obs = CompareTests.write_obs
    def setUp(self):
        CompareTests.setUp(self); self.required=self.d/'required.csv'
    def checklist(self, rows):
        self.write(self.required, ('index','field'), [dict(zip(('index','field'), r)) for r in rows])
    def run_check(self):
        return subprocess.run([sys.executable,'-m','reference.compare_trace',str(self.trace),str(self.obs),'--required',str(self.required)],capture_output=True,text=True)
    def test_complete_checklist(self):
        self.checklist([('20','entry')]); r=self.run_check(); self.assertEqual(r.returncode,0); self.assertIn('1 of 1 planned cell(s) recorded; 0 missing',r.stdout)
    def test_missing_checklist_cell(self):
        self.checklist([('20','entry'),('20','stop')]); r=self.run_check(); self.assertEqual(r.returncode,1); self.assertIn('missing: index 20, stop',r.stdout)
    def test_checklist_does_not_mask_difference(self):
        self.checklist([('20','entry')]); self.write_obs([('20','entry','99')]); r=self.run_check(); self.assertEqual(r.returncode,1); self.assertIn('0 missing',r.stdout); self.assertIn('1 difference(s)',r.stdout)
    def test_extra_observations_still_compared(self):
        self.checklist([('20','entry')]); self.write_obs([('20','entry','100'),('20','state','idle')]); r=self.run_check(); self.assertEqual(r.returncode,1); self.assertIn('1 difference(s)',r.stdout)
    def test_unknown_checklist_index_rejected(self):
        self.checklist([('21','entry')]); self.assertEqual(self.run_check().returncode,2)
    def test_unknown_checklist_field_rejected(self):
        self.checklist([('20','madeup')]); self.assertEqual(self.run_check().returncode,2)
    def test_duplicate_checklist_rejected(self):
        self.checklist([('20','entry'),('020','entry')]); self.assertEqual(self.run_check().returncode,2)
    def test_empty_checklist_rejected(self):
        self.checklist([]); self.assertEqual(self.run_check().returncode,2)
    def test_extra_header_rejected(self):
        self.required.write_text('index,field,extra\n20,entry,foo\n'); self.assertEqual(self.run_check().returncode,2)
    def test_blank_observation_is_present_not_unknown(self):
        self.checklist([('20','cancel_reason')]); self.write_obs([('20','cancel_reason','')]); r=self.run_check(); self.assertEqual(r.returncode,0); self.assertIn('0 missing',r.stdout)
    def test_coverage_summary(self):
        self.checklist([('20','entry')]); r=self.run_check(); self.assertIn('Observations present on 1 of 1 trace bar(s)',r.stdout); self.assertIn('entry: 1 of 1 trace bar(s)',r.stdout)
    def test_empty_observations_report_all_missing(self):
        self.checklist([('20','entry'),('20','stop')]); self.write_obs([]); r=self.run_check(); self.assertEqual(r.returncode,1); self.assertIn('0 of 2 planned cell(s) recorded; 2 missing',r.stdout)
    def test_no_input_writes(self):
        self.checklist([('20','entry')]); before=[p.read_bytes() for p in (self.trace,self.obs,self.required)]; self.assertEqual(self.run_check().returncode,0); self.assertEqual(before,[p.read_bytes() for p in (self.trace,self.obs,self.required)])
    def test_large_missing_is_bounded(self):
        fields=[f for f in FIELDS if f!='entry']; rows=[]
        for i in range(20,23):
            row=dict.fromkeys(('index', *FIELDS),''); row['index']=str(i); row['entry']='100'; rows.append(row)
        self.write(self.trace,('index',*FIELDS),rows); self.checklist([(str(i),f) for i in range(20,23) for f in fields]); r=self.run_check(); self.assertEqual(r.returncode,1); self.assertIn('... and 12 more missing cell(s)',r.stdout)

if __name__ == '__main__': unittest.main()
