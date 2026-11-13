import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from reference.preflight import inspect

FIELDS=('index','day','open','high','low','close','prior_high','prior_low','prior_atr','timestamp','in_session','confirmed','ema','vwap','volume','prior_volume_avg')

def make_row(index=20):
    return dict(zip(FIELDS,(str(index),'2026-01-01','99.5','102','99','101.8','100','95','2','2026-01-01T10:00:00Z','true','true','100','100','100','50')))

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.d=Path(self.tmp.name); self.bars=self.d/'bars.csv'; self.config=self.d/'config.json'; self.write([make_row()])
    def write(self, rows, fields=FIELDS):
        with self.bars.open('w',newline='',encoding='utf8') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    def conf(self, **kw): self.config.write_text(json.dumps(kw)); return self.config
    def messages(self, config=None): return [w[0] for w in inspect(self.bars,config)[1]]
    def run_cli(self,*extra):
        return subprocess.run([sys.executable,'-m','reference.preflight',str(self.bars),*map(str,extra)],capture_output=True,text=True)
    def test_fully_specified_no_warning(self): self.assertEqual(inspect(self.bars),(1,[]))
    def test_missing_flag_defaults_reported(self):
        r=make_row();r.update(in_session='',confirmed='');self.write([r]); text=' '.join(self.messages()); self.assertIn('in_session blank or absent',text);self.assertIn('confirmed blank or absent',text)
    def test_missing_columns_reported(self):
        self.write([make_row()],tuple(x for x in FIELDS if x not in ('in_session','confirmed','timestamp')));self.assertEqual(len(self.messages()),3)
    def test_blank_timestamp(self):
        r=make_row();r['timestamp']='';self.write([r]);self.assertIn('timestamp blank',self.messages()[0])
    def test_naive_timestamp(self):
        r=make_row();r['timestamp']='2026-01-01T10:00:00';self.write([r]);self.assertIn('no timezone offset',self.messages()[0])
    def test_offset_timestamp(self):
        r=make_row();r['timestamp']='2026-01-01T10:00:00+05:30';self.write([r]);self.assertEqual(self.messages(),[])
    def test_unprepared_values(self):
        r=make_row();r.update(prior_high='',prior_low='',prior_atr='');self.write([r]);self.assertIn('breakout detection is skipped',self.messages()[0])
    def test_zero_atr(self):
        r=make_row();r['prior_atr']='0';self.write([r]);self.assertIn('prior ATR is zero',self.messages()[0])
    def test_missing_ema_enabled(self):
        r=make_row();r['ema']='';self.write([r]);self.assertIn('EMA filter enabled',self.messages(self.conf(use_ema=True))[0]);self.assertEqual(self.messages(),[])
    def test_missing_vwap_enabled(self):
        r=make_row();r['vwap']='';self.write([r]);self.assertIn('VWAP filter enabled',self.messages(self.conf(use_vwap=True))[0]);self.assertEqual(self.messages(),[])
    def test_missing_volume_pair_enabled(self):
        r=make_row();r['volume']='';self.write([r]);self.assertIn('volume or prior average missing',self.messages(self.conf(use_volume=True))[0])
    def test_zero_prior_volume(self):
        r=make_row();r['prior_volume_avg']='0';self.write([r]);self.assertIn('prior volume average is zero',self.messages(self.conf(use_volume=True))[0])
    def test_filter_warnings_ignore_unprepared(self):
        r=make_row();r.update(prior_high='',prior_low='',prior_atr='',ema='',vwap='',volume='',prior_volume_avg='');self.write([r]);msgs=self.messages(self.conf(use_ema=True,use_vwap=True,use_volume=True));self.assertEqual(len(msgs),1)
    def test_invalid_ohlc_error(self):
        r=make_row();r['high']='90';self.write([r]);self.assertRaises(ValueError,inspect,self.bars)
    def test_partial_prior_error(self):
        r=make_row();r['prior_atr']='';self.write([r]);self.assertRaises(ValueError,inspect,self.bars)
    def test_unconfirmed_error(self):
        r=make_row();r['confirmed']='false';self.write([r]);self.assertRaises(ValueError,inspect,self.bars)
    def test_nonconsecutive_indexes_error(self): self.write([make_row(20),make_row(22)]);self.assertRaises(ValueError,inspect,self.bars)
    def test_invalid_config_error(self): self.assertRaises(ValueError,inspect,self.bars,self.conf(tick=-1))
    def test_duplicate_header_error(self):
        self.bars.write_text('index,index,day,open,high,low,close,prior_high,prior_low,prior_atr\n20,20,2026-01-01,99.5,102,99,101.8,100,95,2\n');self.assertRaises(ValueError,inspect,self.bars)
    def test_bad_row_error(self):
        self.bars.write_text(','.join(FIELDS)+'\n20,2026-01-01\n');self.assertRaises(ValueError,inspect,self.bars)
    def test_empty_error(self): self.write([]);self.assertRaises(ValueError,inspect,self.bars)
    def test_cli_statuses(self):
        self.assertEqual(self.run_cli('--strict').returncode,0)
        r=make_row();r['in_session']='';self.write([r]);a=self.run_cli();b=self.run_cli('--strict');self.assertEqual(a.returncode,0);self.assertEqual(b.returncode,1);self.assertIn('assumes true',b.stdout)
        self.bars.write_text('bad\n');self.assertEqual(self.run_cli().returncode,2)
    def test_read_only(self):
        self.conf(use_ema=True);before=[p.read_bytes() for p in (self.bars,self.config)];self.assertEqual(self.run_cli('--config',self.config).returncode,0);self.assertEqual(before,[p.read_bytes() for p in (self.bars,self.config)])
    def test_bounded_index_examples(self):
        rows=[make_row(i) for i in range(20,27)]
        for r in rows:r['in_session']=''
        self.write(rows);out=self.run_cli().stdout;line=next(x for x in out.splitlines() if 'in_session blank' in x);self.assertIn('indexes: 20, 21, 22, 23, 24, ...',line);self.assertNotIn('24, 25',line)
    def test_malformed_utf8_cli(self):
        self.bars.write_bytes(b'\xff');self.assertEqual(self.run_cli().returncode,2)
    def test_sample_is_honestly_warned(self):
        root=Path(__file__).resolve().parents[1]; count,warnings=inspect(root/'sample_trace.csv');self.assertEqual(count,3);msgs=' '.join(w[0] for w in warnings);self.assertIn('in_session blank',msgs);self.assertIn('prior high/low/ATR blank',msgs)

if __name__=='__main__': unittest.main()
