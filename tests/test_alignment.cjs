const test=require('node:test'),assert=require('node:assert/strict'),{alignment}=require('../geometry.js');
test('shows lower and higher for misaligned price',()=>assert.deepEqual(alignment('100.001','0.01'),{lower:'100.00',upper:'100.01'}));
test('returns no suggestions when already aligned',()=>assert.equal(alignment('100.00','0.01'),null));
test('handles non-power-of-ten ticks exactly',()=>assert.deepEqual(alignment('10.02','0.05'),{lower:'10.00',upper:'10.05'}));
test('handles minimum precision with integer arithmetic',()=>assert.deepEqual(alignment('0.00000003','0.00000002'),{lower:'0.00000002',upper:'0.00000004'}));
test('does not offer upper beyond supported maximum',()=>assert.deepEqual(alignment('1000000000','0.03'),{lower:'999999999.99',upper:null}));
test('rejects invalid or zero tick',()=>{for(const tick of ['0','-1','1e-2','0.000000001'])assert.throws(()=>alignment('100',tick))});
test('rejects invalid prices',()=>{for(const price of ['','-2','1e2','1000000001'])assert.throws(()=>alignment(price,'0.01'))});
