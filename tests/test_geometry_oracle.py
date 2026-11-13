"""Cross-language synthetic checks: Decimal oracle versus JS geometry.

This checks the standalone calculator only. It is not a Pine-parity test.
Requires Node; skipped when Node is not installed.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import json
import random
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which('node'), 'Node is needed for cross-language calculator checks')
class DecimalOracleTests(unittest.TestCase):
    def test_1200_seeded_long_and_short_examples(self):
        rng=random.Random(1100); cases=[]; expected=[]
        for i in range(1200):
            direction='long' if i%2==0 else 'short'; sign=1 if direction=='long' else -1
            tick=Decimal(rng.choice(['0.01','0.05','0.25','0.0001']))
            risk_ticks=rng.randint(8,400); entry_ticks=1000000
            entry=Decimal(entry_ticks)*tick; stop=Decimal(entry_ticks-sign*risk_ticks)*tick
            # Strictly increasing fractions; enough separation for distinct ticks.
            rs=[Decimal(v)/Decimal(4) for v in (2,4,6,8)]
            target_ticks=[int((Decimal(entry_ticks)+sign*Decimal(risk_ticks)*r).to_integral_value(rounding=ROUND_HALF_UP)) for r in rs]
            cases.append({'direction':direction,'entry':str(entry),'stop':str(stop),'tick':str(tick),'rs':[str(r) for r in rs]})
            distances=[abs(t-entry_ticks) for t in target_ticks]
            expected.append({'targets':[Decimal(t)*tick for t in target_ticks], 'distances':distances,
                             'achieved':[str((Decimal(n)/Decimal(risk_ticks)).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP)) for n in distances],
                             'changed':[Decimal(n)!=Decimal(risk_ticks)*r for n,r in zip(distances,rs)]})
        script="const G=require('./geometry.js');let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(s).map(G.calculate))));"
        proc=subprocess.run(['node','-e',script],cwd=ROOT,input=json.dumps(cases),text=True,capture_output=True,check=True)
        got=json.loads(proc.stdout);self.assertEqual(len(got),len(expected))
        for i,(actual,exp) in enumerate(zip(got,expected)):
            with self.subTest(case=i):
                self.assertEqual([Decimal(v) for v in actual['targets']],exp['targets'])
                self.assertEqual([int(v) for v in actual['targetTicks']],exp['distances'])
                self.assertEqual(actual['achievedR'],exp['achieved'])
                self.assertEqual(actual['roundingChanged'],exp['changed'])

if __name__=='__main__':unittest.main()
