import csv, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from reference.engine import load_config
from reference.preflight import inspect

ROOT=Path(__file__).resolve().parents[1]
FIELDS=['index','day','open','high','low','close','prior_high','prior_low','prior_atr','timestamp','in_session','confirmed']
def row(index,timestamp):
    return dict(zip(FIELDS,[str(index),'2026-01-01','99.5','102','99','101.8','100','95','2',timestamp,'true','true']))
class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name);self.bars=self.p/'bars.csv'
    def rows(self,*items):
        with self.bars.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(items)
    def warnings(self):return [x[0] for x in inspect(self.bars)[1]]
    def trace(self,*args):return subprocess.run([sys.executable,'-m','reference.engine',str(self.bars),*map(str,args)],capture_output=True,text=True)
    def test_embedded_geometry_matches_source(self):
        html=(ROOT/'calculator.html').read_text(); source=(ROOT/'geometry.js').read_text();self.assertIn(source+'</script>',html)
    def test_short_row_rejected_even_when_trailing_optional(self):
        self.bars.write_text(','.join(FIELDS)+'\n0,2026-01-01,99.5,102,99,101.8,100,95,2\n');result=self.trace();self.assertEqual(result.returncode,2);self.assertIn('wrong number of fields',result.stderr)
    def test_explicit_blank_cells_are_valid(self):
        self.rows(row(0,''));self.assertEqual(self.trace().returncode,0)
    def test_duplicate_config_key_rejected_in_cli(self):
        self.rows(row(0,''));cfg=self.p/'cfg.json';cfg.write_text('{"tick":0.01,"tick":0.05}');result=self.trace('--config',cfg);self.assertEqual(result.returncode,2);self.assertIn('duplicate config key',result.stderr)
    def test_repeated_instants_across_offsets_warn(self):
        self.rows(row(0,'2026-01-01T10:00:00Z'),row(1,'2026-01-01T11:00:00+01:00'));self.assertTrue(any('repeat the same instant' in x for x in self.warnings()))
    def test_backwards_instants_warn(self):
        self.rows(row(0,'2026-01-01T10:00:00Z'),row(1,'2026-01-01T09:00:00Z'));self.assertTrue(any('go backwards' in x for x in self.warnings()))
    def test_ascending_different_offsets_no_warning(self):
        self.rows(row(0,'2026-01-01T10:00:00Z'),row(1,'2026-01-01T11:01:00+01:00'));self.assertEqual(self.warnings(),[])
    def test_naive_breaks_comparison_chain(self):
        self.rows(row(0,'2026-01-01T10:00:00Z'),row(1,'2026-01-01T09:00:00'),row(2,'2026-01-01T08:00:00Z'));w=self.warnings();self.assertTrue(any('no timezone offset' in x for x in w));self.assertFalse(any('go backwards' in x for x in w))
    def test_blank_breaks_comparison_chain(self):
        self.rows(row(0,'2026-01-01T10:00:00Z'),row(1,''),row(2,'2026-01-01T08:00:00Z'));self.assertFalse(any('go backwards' in x for x in self.warnings()))
    def test_strict_timestamp_warning_status(self):
        self.rows(row(0,'2026-01-01T10:00:00Z'),row(1,'2026-01-01T10:00:00Z'));p=subprocess.run([sys.executable,'-m','reference.preflight',str(self.bars),'--strict'],capture_output=True,text=True);self.assertEqual(p.returncode,1);self.assertIn('repeat',p.stdout)
if __name__=='__main__':unittest.main()
