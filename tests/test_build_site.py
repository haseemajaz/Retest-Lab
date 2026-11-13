import base64
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from build_site import build, MARKER

class SiteBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name)
        self.z=self.d/'package.zip';self.g=self.d/'guide.docx';self.out=self.d/'site.html'
        for p in (self.z,self.g):
            with zipfile.ZipFile(p,'w') as f:f.writestr('example.txt','synthetic')
    def test_embeds_exact_bytes_and_names(self):
        build(self.z,self.g,self.out);s=self.out.read_text();self.assertNotIn(MARKER,s)
        data=json.loads(re.search(r'const embeddedDownloads = (\{.*?\});',s).group(1))
        self.assertEqual(base64.b64decode(data['zip']['base64']),self.z.read_bytes());self.assertEqual(data['zip']['name'],self.z.name)
        self.assertEqual(base64.b64decode(data['guide']['base64']),self.g.read_bytes());self.assertEqual(data['guide']['name'],self.g.name)
    def test_never_overwrites_existing_output(self):
        self.out.write_text('preserve');self.assertRaises(FileExistsError,build,self.z,self.g,self.out);self.assertEqual(self.out.read_text(),'preserve')
    def test_refuses_invalid_archive(self):
        self.z.write_text('not zip');self.assertRaises(ValueError,build,self.z,self.g,self.out);self.assertFalse(self.out.exists())
    def test_refuses_existing_input_as_output(self):
        before=self.z.read_bytes();self.assertRaises(FileExistsError,build,self.z,self.g,self.z);self.assertEqual(self.z.read_bytes(),before)

if __name__=='__main__':unittest.main()
