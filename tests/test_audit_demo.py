from pathlib import Path
import hashlib,unittest
ROOT=Path(__file__).resolve().parents[1]
class DemoTests(unittest.TestCase):
 def test_demo_labels_and_hashes_match_samples(self):
  s=(ROOT/'DEMO_AUDIT.html').read_text();self.assertIn('Synthetic demonstration.',s)
  for name in ('sample_trace.csv','sample_observations.csv','sample_required.csv'):
   self.assertIn(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),s)
if __name__=='__main__':unittest.main()
