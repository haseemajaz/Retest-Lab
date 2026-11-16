from pathlib import Path
import json,re,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
class ViewerIntegrity(unittest.TestCase):
 def test_embedded_source_matches_tested_module(self):
  self.assertIn((ROOT/'trace_viewer.js').read_text()+'</script>',(ROOT/'TRACE_VIEWER.html').read_text())
 def test_embedded_sample_matches_engine_output(self):
  html=(ROOT/'TRACE_VIEWER.html').read_text(); match=re.search(r'const SAMPLE=(".*?"), \$=',html);self.assertIsNotNone(match);sample=json.loads(match.group(1));p=subprocess.run([sys.executable,'-m','reference.engine','sample_trace.csv'],cwd=ROOT,capture_output=True,text=True,check=True);self.assertEqual(sample,p.stdout)
if __name__=='__main__':unittest.main()
