import csv,json,tempfile,unittest
from pathlib import Path
from reference.preflight import inspect
FIELDS=['index','day','open','high','low','close','prior_high','prior_low','prior_atr','timestamp','in_session','confirmed']
def row():return dict(zip(FIELDS,['0','2026-01-01','1.0','2.0','0.5','1.5','1.2','0.8','0.2','2026-01-01T00:00:00Z','true','true']))
class PrecisionTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'bars.csv';self.c=Path(self.t.name)/'config.json'
 def write(self,r):
  with self.p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerow(r)
 def msgs(self,config=None):return ' '.join(x[0] for x in inspect(self.p,config)[1])
 def test_short_decimal_does_not_prove_exact_float(self):
  self.write(row());self.assertNotIn('decimal input changes',self.msgs())
 def test_long_decimal_changes(self):
  r=row();r['open']='1.00000000000000001';self.write(r);self.assertIn('decimal input changes',self.msgs())
 def test_underflow_changes(self):
  r=row();r['prior_atr']='1e-400';self.write(r);self.assertIn('decimal input changes',self.msgs())
 def test_derived_decimal_changes(self):
  r=row();r['prior_high']='1.20000000000000001';self.write(r);self.assertIn('decimal input changes',self.msgs())
 def test_scientific_equivalent_no_warning(self):
  r=row();r['open']='1e0';self.write(r);self.assertNotIn('decimal input changes',self.msgs())
 def test_grid_resolution_threshold(self):
  r=row();r.update(open='9007199254740992',high='9007199254740992',low='9007199254740992',close='9007199254740992');self.write(r);self.c.write_text('{"tick":1}');self.assertIn('2^53',self.msgs(self.c))
 def test_small_tick_resolution(self):
  self.write(row());self.c.write_text('{"tick":1e-10}');self.assertNotIn('2^53',self.msgs(self.c))
 def test_input_not_written(self):
  self.write(row());before=self.p.read_bytes();inspect(self.p);self.assertEqual(before,self.p.read_bytes())
if __name__=='__main__':unittest.main()
