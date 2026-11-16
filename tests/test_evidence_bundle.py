import hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from reference.audit_report import parse_bundle,MAX_INPUT
ROOT=Path(__file__).resolve().parents[1]
class BundleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.bundle=self.d/'bundle.json';self.out=self.d/'report.html';self.bars=ROOT/'sample_trace.csv'
 def write(self,req='index,field\n20,events\n',obs='index,field,value\n20,events,armed_long\n'):
  self.bundle.write_text(json.dumps(['retest-evidence',1,req,obs]),encoding='utf-8')
 def runcli(self,*extra):return subprocess.run([sys.executable,'-m','reference.audit_report','--bars',str(self.bars),'--bundle',str(self.bundle),'--output',str(self.out),*map(str,extra)],cwd=ROOT,text=True,capture_output=True)
 def test_parse_exact(self):
  b=json.dumps(['retest-evidence',1,'x','y']).encode();self.assertEqual(parse_bundle(b),(b'x',b'y'))
 def test_reject_boolean_version(self):
  with self.assertRaises(ValueError):parse_bundle(b'["retest-evidence",true,"x","y"]')
 def test_wrong_format_and_types(self):
  for x in [['retest-capture',1,[],[]],['retest-evidence',2,'',''],['retest-evidence',1,[], ''],['retest-evidence',1,''],{}]:
   with self.subTest(x=x),self.assertRaises(ValueError):parse_bundle(json.dumps(x).encode())
 def test_nonstandard_json_and_invalid_unicode(self):
  for b in [b'["retest-evidence",NaN,"", ""]', b'\xff',b'["retest-evidence",1,"\\ud800",""]',b'['*1100+b']'*1100]:
   with self.subTest(b=b[:60]),self.assertRaises(ValueError):parse_bundle(b)
 def test_valid_bundle_creates_report_and_hashes_original(self):
  self.write();raw=self.bundle.read_bytes();p=self.runcli();self.assertEqual(p.returncode,0,p.stderr);s=self.out.read_text();self.assertIn('1 of 1 planned cells recorded',s);self.assertIn(hashlib.sha256(raw).hexdigest(),s);self.assertEqual(self.bundle.read_bytes(),raw)
 def test_missing_is_not_pass(self):
  self.write(obs='index,field,value\n');p=self.runcli();self.assertEqual(p.returncode,1,p.stderr);self.assertIn('1</b><span>missing planned cells',self.out.read_text())
 def test_recorded_blank_is_present(self):
  self.write('index,field\n20,cancel_reason\n','index,field,value\n20,cancel_reason,\n');p=self.runcli();self.assertEqual(p.returncode,0,p.stderr);self.assertIn('1 of 1 planned cells recorded',self.out.read_text())
 def test_mismatch_returns_one(self):
  self.write(obs='index,field,value\n20,events,wrong\n');self.assertEqual(self.runcli().returncode,1)
 def test_extra_observation_rejected(self):
  self.write(obs='index,field,value\n20,events,armed_long\n20,cancel_reason,\n');p=self.runcli();self.assertEqual(p.returncode,2);self.assertIn('not present in its checklist',p.stderr);self.assertFalse(self.out.exists())
 def test_duplicate_checklist_rejected(self):
  self.write('index,field\n20,events\n020,events\n');self.assertEqual(self.runcli().returncode,2);self.assertFalse(self.out.exists())
 def test_duplicate_observation_rejected(self):
  self.write(obs='index,field,value\n20,events,armed_long\n20,events,armed_long\n');self.assertEqual(self.runcli().returncode,2)
 def test_empty_checklist_rejected(self):
  self.write('index,field\n','index,field,value\n');self.assertEqual(self.runcli().returncode,2)
 def test_malformed_csv_rejected(self):
  self.write(obs='index,field,value\n20,events\n');self.assertEqual(self.runcli().returncode,2)
 def test_unknown_index_rejected(self):
  self.write('index,field\n999,events\n','index,field,value\n');self.assertEqual(self.runcli().returncode,2)
 def test_no_mixed_input_modes(self):
  self.write();p=self.runcli('--observations',ROOT/'sample_observations.csv');self.assertEqual(p.returncode,2);self.assertIn('cannot be combined',p.stderr);self.assertFalse(self.out.exists())
 def test_existing_destination_preserved(self):
  self.write();self.out.write_text('existing');self.assertEqual(self.runcli().returncode,2);self.assertEqual(self.out.read_text(),'existing')
 def test_oversize_rejected(self):
  self.bundle.write_bytes(b' '*(MAX_INPUT+1));self.assertEqual(self.runcli().returncode,2);self.assertFalse(self.out.exists())
 @unittest.skipUnless(shutil.which('node'),'Node required for JavaScript integration')
 def test_javascript_bundle_to_audit(self):
  js="const c=require('./capture.js'); console.log(c.bundle([{index:'20',field:'events',recorded:true,value:'armed_long'},{index:'21',field:'events',recorded:false,value:'pending'}]))"
  self.bundle.write_text(subprocess.check_output(['node','-e',js],cwd=ROOT,text=True),encoding='utf-8');r=self.runcli();self.assertEqual(r.returncode,1,r.stderr);s=self.out.read_text();self.assertIn('1 of 2 planned cells recorded',s);self.assertNotIn('pending',s)
if __name__=='__main__':unittest.main()
