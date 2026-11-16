const {test}=require('node:test'), assert=require('node:assert/strict'), c=require('../capture.js');
const row=(p={})=>({index:'20',field:'events',recorded:true,value:'armed_long',...p});
test('bundle is versioned and contains both CSVs from one snapshot',()=>{const rows=[row(),row({index:'21',recorded:false,value:'not observed'})], b=JSON.parse(c.bundle(rows)), files=c.csv(rows);assert.deepEqual(b,['retest-evidence',1,files.required,files.observations]);assert(!b[3].includes('not observed'))});
test('recorded blank remains present',()=>{const b=JSON.parse(c.bundle([row({field:'cancel_reason',value:''})]));assert.match(b[3],/20,cancel_reason,\r\n/) });
test('unchecked blank stays missing',()=>{const b=JSON.parse(c.bundle([row({recorded:false,value:''})]));assert.equal(b[3],'index,field,value\r\n')});
test('bundle rejects empty or duplicate plan',()=>{assert.throws(()=>c.bundle([]));assert.throws(()=>c.bundle([row(),row({index:'020'})]),/duplicate/)});
test('bundle preserves comma quotes newline and unicode',()=>{const r=row({value:'a,"b"\n🧪'});const b=JSON.parse(c.bundle([r]));assert.equal(b[3],c.csv([r]).observations)});
test('bundle is a snapshot not a live view',()=>{const r=row(),b=c.bundle([r]);r.value='changed';assert(!b.includes('changed'));assert(b.includes('armed_long'))});
test('bundle and editable backup have distinct formats',()=>{assert.throws(()=>c.restore(c.bundle([row()])),/Unsupported/)});
