"""Ensure browser-generated CSV remains compatible with Python comparison."""
import csv, json, shutil, subprocess, tempfile, unittest
from pathlib import Path
from reference.compare_trace import compare_detailed, read_requirements
from reference.engine import load_config, trace_rows
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which('node'), 'Node required for capture integration')
class CaptureIntegration(unittest.TestCase):
 def test_generated_files_compare_and_distinguish_blank_missing(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d)
   js="const c=require('./capture.js');console.log(JSON.stringify(c.csv([{index:'20',field:'events',recorded:true,value:'armed_long'},{index:'20',field:'cancel_reason',recorded:true,value:''},{index:'21',field:'events',recorded:false,value:'ignored'}])))"
   result=json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT,text=True))
   (d/'req.csv').write_text(result['required']);(d/'obs.csv').write_text(result['observations'])
   with (ROOT/'sample_trace.csv').open(newline='') as f: trace=trace_rows(csv.DictReader(f),load_config(None))
   with (d/'trace.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
   count,diffs,indexes,seen=compare_detailed(d/'trace.csv',d/'obs.csv',True)
   self.assertEqual(count,2);self.assertEqual(diffs,[]);self.assertEqual(read_requirements(d/'req.csv',indexes)-seen,{(21,'events')})
if __name__=='__main__':unittest.main()
