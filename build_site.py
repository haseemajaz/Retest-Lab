"""Build the single-file landing site from the outer package ZIP and guide."""
import argparse
import base64
import json
from pathlib import Path
import sys
import zipfile

TEMPLATE = Path(__file__).resolve().parent / 'website.template'
MARKER = '__EMBEDDED_DOWNLOADS__'

def build(zip_path, guide_path, output):
    zip_path, guide_path, output = map(Path, (zip_path, guide_path, output))
    if not zipfile.is_zipfile(zip_path) or not zipfile.is_zipfile(guide_path):
        raise ValueError('ZIP and Word guide must be valid ZIP-based files')
    template = TEMPLATE.read_text(encoding='utf-8')
    if template.count(MARKER) != 1: raise ValueError('website template marker missing or duplicated')
    data = {}
    for key, path, mime in [('zip',zip_path,'application/zip'),('guide',guide_path,'application/vnd.openxmlformats-officedocument.wordprocessingml.document')]:
        data[key] = {'base64':base64.b64encode(path.read_bytes()).decode('ascii'),'name':path.name,'type':mime}
    html = template.replace(MARKER,json.dumps(data,separators=(',',':')))
    # Exclusive creation avoids replacing any existing evidence or source.
    with output.open('x',encoding='utf-8',newline='') as f: f.write(html)

def main(argv=None):
    p=argparse.ArgumentParser(description='Build a standalone website; refuses to overwrite an existing output.')
    p.add_argument('--zip',required=True,help='outer software ZIP')
    p.add_argument('--guide',required=True,help='included Word guide')
    p.add_argument('--output',required=True,help='new HTML output filename')
    a=p.parse_args(argv)
    try: build(a.zip,a.guide,a.output)
    except (OSError,ValueError,UnicodeError) as exc:
        print('Site build error: '+str(exc),file=sys.stderr);return 2
    print('Built '+a.output+'; no existing file was replaced.');return 0
if __name__=='__main__': raise SystemExit(main())
