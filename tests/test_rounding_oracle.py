"""Cross-check JS tick indexes against Decimal and Python float arithmetic."""
import json, math, random, shutil, subprocess, unittest
from decimal import Decimal, localcontext, ROUND_FLOOR
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which('node'),'Node required for cross-language oracle')
class RoundingOracle(unittest.TestCase):
 def test_seeded_cases(self):
  rng=random.Random(20261114)
  cases=[['0.0049999999995','0.01'],['-0.0050000000005','0.01'],['-0.005','0.01'],['0.005','0.01']]
  for _ in range(600):
   p=rng.randrange(-10000000000000,10000000000000); tick=rng.randrange(1,100000000)
   cases.append([str(Decimal(p)/Decimal(10**10)),str(Decimal(tick)/Decimal(10**8))])
  js="const r=require('./rounding_inspector.js');const fs=require('fs');const a=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(a.map(x=>r.compare(...x))))"
  output=json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT,input=json.dumps(cases),text=True))
  with localcontext() as ctx:
   ctx.prec=100
   for (p,t),got in zip(cases,output):
    ideal=int((Decimal(p)/Decimal(t)+Decimal('0.5')).to_integral_value(rounding=ROUND_FLOOR))
    floating=math.floor(float(p)/float(t)+0.5+1e-10)
    self.assertEqual(got['exactTicks'],str(ideal),(p,t));self.assertEqual(got['modelTicks'],str(floating),(p,t))
    self.assertEqual(Decimal(got['exactPrice']),Decimal(ideal)*Decimal(t));self.assertEqual(got['different'],ideal!=floating)
 def test_boundary_and_large_ratio_cases(self):
  # Decimal oracle across positive/negative half-tick boundaries and both
  # sides, including ratios close to 2^40; prices remain within UI limits.
  rng=random.Random(20261115);cases=[]
  with localcontext() as ctx:
   ctx.prec=100
   for _ in range(2500):
    tick=Decimal(rng.choice(['0.0000000001','0.000001','0.01','0.25','1']))
    k=rng.choice([rng.randrange(-1000000,1000000),rng.randrange(2**40-1000,2**40-2),-rng.randrange(2**40-1000,2**40-2)])
    offset=Decimal(rng.choice(['-0.00000001','0','0.00000001']))
    price=(Decimal(k)+Decimal('0.5')+offset)*tick
    # Inspector accepts <=16 decimal places, 12 whole digits, <=2^40 ticks.
    p=format(price,'f').rstrip('0').rstrip('.') if '.' in format(price,'f') else format(price,'f')
    t=format(tick,'f')
    if len(p.lstrip('-').split('.')[0])<=12 and len(p.split('.')[1] if '.' in p else '')<=16 and abs(price)<=tick*Decimal(2**40):cases.append([p,t])
   js="const r=require('./rounding_inspector.js');const fs=require('fs');let a=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(a.map(x=>r.compare(...x))))"
   output=json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT,input=json.dumps(cases),text=True))
   self.assertGreater(len(cases),1500)
   for (p,t),got in zip(cases,output):
    ideal=int((Decimal(p)/Decimal(t)+Decimal('0.5')).to_integral_value(rounding=ROUND_FLOOR));floating=math.floor(float(p)/float(t)+0.5+1e-10)
    self.assertEqual(got['exactTicks'],str(ideal),(p,t));self.assertEqual(got['modelTicks'],str(floating),(p,t))
    self.assertEqual(Decimal(got['exactPrice']),Decimal(ideal)*Decimal(t));self.assertEqual(got['different'],ideal!=floating)
if __name__=='__main__':unittest.main()
