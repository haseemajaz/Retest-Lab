import csv, hashlib, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from reference import audit_report as a
ROOT=Path(__file__).resolve().parents[1]
class AuditTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=Path(self.temp.name)
  self.bars=self.p/'bars.csv';self.bars.write_bytes((ROOT/'sample_trace.csv').read_bytes())
  self.obs=self.p/'observations.csv';self.obs.write_bytes((ROOT/'sample_observations.csv').read_bytes())
  self.req=self.p/'required.csv';self.req.write_bytes((ROOT/'sample_required.csv').read_bytes())
  self.out=self.p/'audit.html'
 def run_cli(self,*extra):return subprocess.run([sys.executable,'-m','reference.audit_report','--bars',str(self.bars),'--output',str(self.out),*map(str,extra)],cwd=ROOT,capture_output=True,text=True)
 def html(self):return self.out.read_text(encoding='utf-8')
 def test_without_observations_is_not_run(self):
  p=self.run_cli();self.assertEqual(p.returncode,0,p.stderr);self.assertIn('<strong>Not run.</strong>',self.html());self.assertNotIn('No differences or missing',self.html())
 def test_comparison_and_checklist(self):
  p=self.run_cli('--observations',self.obs,'--required',self.req);self.assertEqual(p.returncode,0,p.stderr);s=self.html();self.assertIn('5 of 5 planned cells recorded',s);self.assertIn('<b>0</b><span>differences',s)
 def test_source_hashes_are_snapshot_bytes(self):
  self.run_cli('--observations',self.obs);s=self.html();self.assertIn(hashlib.sha256(self.bars.read_bytes()).hexdigest(),s);self.assertIn(hashlib.sha256(self.obs.read_bytes()).hexdigest(),s)
 def test_default_config_rendered(self):
  self.run_cli();self.assertIn('&quot;tick&quot;: 0.01',self.html())
 def test_custom_config_in_report(self):
  cfg=self.p/'config.json';cfg.write_text('{"tick":0.05}');p=self.run_cli('--config',cfg);self.assertEqual(p.returncode,0,p.stderr);self.assertIn('&quot;tick&quot;: 0.05',self.html())
 def test_strict_warning_returns_one_with_report(self):
  p=self.run_cli('--strict');self.assertEqual(p.returncode,1,p.stderr);self.assertTrue(self.out.exists())
 def test_difference_returns_one(self):
  self.obs.write_text('index,field,value\n20,events,not_it\n');p=self.run_cli('--observations',self.obs);self.assertEqual(p.returncode,1,p.stderr);self.assertIn('Observed: <code>not_it</code>',self.html())
 def test_missing_required_returns_one(self):
  self.obs.write_text('index,field,value\n20,events,armed_long\n');p=self.run_cli('--observations',self.obs,'--required',self.req);self.assertEqual(p.returncode,1,p.stderr);self.assertIn('4</b><span>missing planned cells',self.html())
 def test_empty_observations_allowed_with_checklist(self):
  self.obs.write_text('index,field,value\n');p=self.run_cli('--observations',self.obs,'--required',self.req);self.assertEqual(p.returncode,1,p.stderr);self.assertIn('0</b><span>recorded cells',self.html())
 def test_empty_observations_without_checklist_is_error(self):
  self.obs.write_text('index,field,value\n');p=self.run_cli('--observations',self.obs);self.assertEqual(p.returncode,2);self.assertFalse(self.out.exists())
 def test_required_without_observations_is_error(self):
  self.assertEqual(self.run_cli('--required',self.req).returncode,2);self.assertFalse(self.out.exists())
 def test_unknown_observation_index_rejected(self):
  self.obs.write_text('index,field,value\n99,events,foo\n');self.assertEqual(self.run_cli('--observations',self.obs).returncode,2);self.assertFalse(self.out.exists())
 def test_bad_config_rejected(self):
  c=self.p/'config';c.write_text('{"tick": 0}');self.assertEqual(self.run_cli('--config',c).returncode,2);self.assertFalse(self.out.exists())
 def test_bad_bars_rejected_without_output(self):
  self.bars.write_text('bad\n');self.assertEqual(self.run_cli().returncode,2);self.assertFalse(self.out.exists())
 def test_existing_output_no_clobber(self):
  self.out.write_text('preserve');self.assertEqual(self.run_cli().returncode,2);self.assertEqual(self.out.read_text(),'preserve')
 def test_input_as_output_no_clobber(self):
  before=self.bars.read_bytes();self.out=self.bars;self.assertEqual(self.run_cli().returncode,2);self.assertEqual(self.bars.read_bytes(),before)
 def test_output_symlink_not_followed(self):
  other=self.p/'victim';other.write_text('safe');self.out.symlink_to(other);self.assertEqual(self.run_cli().returncode,2);self.assertEqual(other.read_text(),'safe')
 def test_broken_symlink_not_overwritten(self):
  self.out.symlink_to(self.p/'missing');self.assertEqual(self.run_cli().returncode,2);self.assertTrue(self.out.is_symlink())
 def test_inputs_never_modified(self):
  before=[x.read_bytes() for x in (self.bars,self.obs,self.req)];self.run_cli('--observations',self.obs,'--required',self.req);self.assertEqual(before,[x.read_bytes() for x in (self.bars,self.obs,self.req)])
 def test_malformed_utf8_no_report(self):
  self.bars.write_bytes(b'\xff');self.assertEqual(self.run_cli().returncode,2);self.assertFalse(self.out.exists())
 def test_oversize_rejected(self):
  self.bars.write_bytes(b'x'*(a.MAX_INPUT+1));self.assertEqual(self.run_cli().returncode,2);self.assertFalse(self.out.exists())
 def test_values_escaped_and_truncated(self):
  self.obs.write_text('index,field,value\n20,events,<script>alert(1)</script>'+('x'*500)+'\n');self.assertEqual(self.run_cli('--observations',self.obs).returncode,1);s=self.html();self.assertNotIn('<script>',s);self.assertIn('&lt;script&gt;',s);self.assertIn('[truncated]',s)
 def test_filename_escaped(self):
  name=self.p/'<b>evil.csv';name.write_bytes(self.bars.read_bytes());self.bars=name;self.run_cli();self.assertIn('&lt;b&gt;evil.csv',self.html());self.assertNotIn('<b>evil.csv',self.html())
 def test_no_external_resources_or_scripts(self):
  self.run_cli();s=self.html();self.assertNotIn('<script',s);self.assertNotIn('https://',s);self.assertNotIn('http://',s)
 def test_temporary_output_cleaned(self):
  self.run_cli();self.assertEqual(list(self.p.glob('.retest-audit-*')),[])
 def test_original_mutation_after_snapshot_not_used(self):
  original=self.bars.read_bytes();real=a.inspect
  def mutate(*args,**kw):self.bars.write_text('changed after snapshot');return real(*args,**kw)
  opts=type('Options',(),dict(bars=str(self.bars),output=str(self.out),config=None,observations=None,required=None,check_tick=False,strict=False))()
  with patch.object(a,'inspect',side_effect=mutate):self.assertEqual(a.build(opts),0)
  self.assertIn(hashlib.sha256(original).hexdigest(),self.html());self.assertIn('3</b><span>modeled bars',self.html())
 def test_ambiguity_shown_in_report(self):
  import shutil
  shutil.copy(ROOT/'sample_order_ambiguity.csv', self.bars)
  p=self.run_cli(); self.assertEqual(p.returncode,0,p.stderr); s=self.html()
  self.assertIn('stop_vs_target|target_order', s)
  self.assertIn('1 of 3 bar(s) have intrabar order ambiguity', s)
  self.assertIn('<th scope="col">Order ambiguity</th>', s)

 def test_ambiguity_summary_and_reject_counts(self):
  import shutil
  shutil.copy(ROOT/'sample_order_ambiguity.csv', self.bars)
  p=self.run_cli(); self.assertEqual(p.returncode,0,p.stderr); s=self.html()
  self.assertIn('Flagged bars, counted separately', s)
  self.assertIn('<b>1</b><span>ambiguous bars', s)
  self.assertIn('stop_vs_target', s)
  self.assertIn('Flagged bars are excluded from any win/loss-like count', s)
  shutil.copy(ROOT/'sample_reject.csv', self.bars)
  self.out.unlink()
  p=self.run_cli(); self.assertEqual(p.returncode,0,p.stderr); s=self.html()
  self.assertIn('<b>weak_body</b> — 1 bar(s)', s)
  self.assertIn('<b>close_edge</b> — 1 bar(s)', s)
  self.assertIn('<th scope="col">Reject reason</th>', s)
  self.assertIn('Rejected while idle: 3 bar(s), most common reason: close_edge.', s)

 def test_reject_column_blank_on_armed_active_bars(self):
  p=self.run_cli(); self.assertEqual(p.returncode,0,p.stderr); s=self.html()
  self.assertIn('<th scope="col">Reject reason</th>', s)
  self.assertIn('Rejected while idle: 0 bar(s).', s)
  self.assertIn('No rejection reason recorded.', s)

 def test_tick_mode_label(self):
  self.run_cli('--check-tick');self.assertIn('Tick-grid check: enabled',self.html())
 def test_blank_observed_value_is_not_missing(self):
  self.obs.write_text('index,field,value\n20,cancel_reason,\n');self.req.write_text('index,field\n20,cancel_reason\n');self.assertEqual(self.run_cli('--observations',self.obs,'--required',self.req).returncode,0);self.assertIn('1 of 1 planned cells recorded',self.html())
 def test_duplicate_observation_is_error(self):
  self.obs.write_text('index,field,value\n20,events,a\n20,events,b\n');self.assertEqual(self.run_cli('--observations',self.obs).returncode,2);self.assertFalse(self.out.exists())
 def test_mismatch_and_missing_are_both_shown(self):
  self.obs.write_text('index,field,value\n20,events,wrong\n');self.assertEqual(self.run_cli('--observations',self.obs,'--required',self.req).returncode,1);s=self.html();self.assertIn('Observed: <code>wrong</code>',s);self.assertIn('Missing planned observation',s)
 def test_no_checklist_not_assessed(self):
  self.assertEqual(self.run_cli('--observations',self.obs).returncode,0);self.assertIn('No checklist supplied; planned coverage was not assessed.',self.html());self.assertIn('—</b><span>missing planned cells',self.html())
 def test_missing_parent_fails_cleanly(self):
  self.out=self.p/'missing'/'report.html';p=self.run_cli();self.assertEqual(p.returncode,2);self.assertIn('Audit error:',p.stderr);self.assertNotIn('Traceback',p.stderr)
 def test_overlong_details_are_bounded(self):
  r={'bars':[{'index':i,'timestamp':'','state_before':'idle','state':'idle','events':'test','cancel_reason':''} for i in range(30)],'warnings':[],'comparison':(60,[(i,'events','a','b') for i in range(60)],set(range(60)),set()),'checklist':set(),'missing':[],'config':{},'sources':{},'check_tick':False,'strict':False}
  report=a.render_report(r);self.assertIn('First 25 of 30 event-bearing bars',report);self.assertIn('Details limited to the first 50 differences',report);self.assertNotIn('Bar 50 ·',report)
 def test_complete_preflight_no_warning(self):
  data=self.bars.read_text().splitlines();headers=data[0]+',in_session,confirmed';rows=[line+',true,true' for line in data[1:2]];self.bars.write_text(headers+'\n'+'\n'.join(rows)+'\n');self.assertEqual(self.run_cli('--strict').returncode,0);self.assertIn('No preflight warnings reported',self.html())
if __name__=='__main__':unittest.main()
