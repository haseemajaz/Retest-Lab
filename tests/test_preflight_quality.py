import csv, subprocess, sys, tempfile, unittest
from pathlib import Path
from reference.preflight import inspect
FIELDS=['index','day','open','high','low','close','prior_high','prior_low','prior_atr','timestamp','in_session','confirmed']
def row(i,t='2026-01-01T10:00:00Z'):
    return dict(zip(FIELDS,[str(i),'2026-01-01','99.50','102.00','99.00','101.80','100','95','2',t,'true','true']))
class Quality(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'bars.csv';self.cfg=Path(self.t.name)/'config.json'
    def write(self,rows,fields=FIELDS):
        with self.p.open('w',newline='',encoding='utf8') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    def msgs(self,check=False,config=None):return ' '.join(x[0] for x in inspect(self.p,config,check_tick=check)[1])
    def test_unknown(self):
        r=row(0);r['in_sesion']='false';self.write([r],FIELDS+['in_sesion']);self.assertIn("'in_sesion'",self.msgs())
    def test_unknown_blank(self):
        r=row(0);r['note']='';self.write([r],FIELDS+['note']);self.assertIn('ignored by trace',self.msgs())
    def test_unknown_indexes(self):
        rs=[row(i) for i in range(3)];[r.update(note='x') for r in rs];self.write(rs,FIELDS+['note']);self.assertEqual(inspect(self.p)[1][0][1],[0,1,2])
    def test_grid_opt_in(self):
        r=row(0);r['open']='99.501';self.write([r]);self.assertNotIn('tick grid',self.msgs());self.assertIn('tick grid',self.msgs(True))
    def test_grid_decimal_negative_scientific(self):
        r=row(0);r.update(open='-0.25',high='1e0',low='-1.00',close='0');self.write([r]);self.cfg.write_text('{"tick":0.25}');self.assertNotIn('tick grid',self.msgs(True,self.cfg))
    def test_config_tick(self):
        r=row(0);r['open']='99.51';self.write([r]);self.cfg.write_text('{"tick":0.05}');self.assertIn('tick grid',self.msgs(True,self.cfg))
    def test_aligned_grid_is_clear(self):
        self.write([row(0)]);self.assertNotIn('tick grid',self.msgs(True))
    def test_indicator_not_checked(self):
        r=row(0);r['ema']='100.001';self.write([r],FIELDS+['ema']);self.assertNotIn('tick grid',self.msgs(True))
    def test_bounded_precision(self):
        r=row(0);r['open']='99.'+'0'*101;self.write([r]);self.assertIn('tick-grid check skipped',self.msgs(True))
    def test_reverse_across_blank(self):
        self.write([row(0),row(1,''),row(2,'2026-01-01T09:00:00Z')]);self.assertIn('go backwards across',self.msgs())
    def test_duplicate_across_naive(self):
        self.write([row(0),row(1,'2026-01-01T11:00:00'),row(2,'2026-01-01T11:00:00+01:00')]);self.assertIn('repeat across',self.msgs())
    def test_increase_across_gap(self):
        self.write([row(0),row(1,''),row(2,'2026-01-01T11:00:00Z')]);self.assertNotIn('across missing or naive',self.msgs())
    def test_adjacent_no_duplicate_gap_warning(self):
        self.write([row(0),row(1)]);m=self.msgs();self.assertIn('repeat the same instant',m);self.assertNotIn('repeat across',m)
    def test_cli_strict_readonly(self):
        r=row(0);r['open']='99.501';self.write([r]);before=self.p.read_bytes();p=subprocess.run([sys.executable,'-m','reference.preflight',str(self.p),'--strict','--check-tick'],capture_output=True,text=True);self.assertEqual(p.returncode,1);self.assertIn('tick grid',p.stdout);self.assertEqual(self.p.read_bytes(),before)
if __name__=='__main__':unittest.main()
