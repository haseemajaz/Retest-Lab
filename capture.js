/* Offline observation capture. No model predictions, storage or network access. */
(function(root, factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.RetestCapture=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const FIELDS=['timestamp','day','state_before','state','events','cancel_reason','direction','entry','stop','t1','t2','t3','t4','fills_today','targets_hit','order_ambiguity','reject_reason'];
 const MAX_ROWS=500, MAX_VALUE=1024, MAX_INDEX=64, MAX_BACKUP_BYTES=4*1024*1024;
 function validate(rows){
  if(!Array.isArray(rows)||rows.length===0) throw Error('Add at least one planned cell.');
  if(rows.length>MAX_ROWS) throw Error('Maximum 500 planned cells.');
  const seen=new Set(), normalized=[];
  rows.forEach((r,i)=>{
   const where='Row '+(i+1)+': ';
   if(!r||typeof r.index!=='string'||!/^[0-9]+$/.test(r.index)||!Number.isSafeInteger(Number(r.index)))throw Error(where+'enter a nonnegative safe integer index.');
   const index=String(Number(r.index));
   if(!FIELDS.includes(r.field))throw Error(where+'choose a supported field.');
   if(typeof r.recorded!=='boolean'||typeof r.value!=='string')throw Error(where+'invalid observation.');
   if(r.value.length>MAX_VALUE)throw Error(where+'value exceeds 1,024 characters.');
   const key=index+':'+r.field;if(seen.has(key))throw Error(where+'duplicate index and field.');seen.add(key);
   normalized.push({index,field:r.field,recorded:r.recorded,value:r.value});
  });return normalized;
 }
 function quote(x){x=String(x);return /[",\r\n]/.test(x)?'"'+x.replace(/"/g,'""')+'"':x;}
 function csv(rows){const v=validate(rows);const lines=(items)=>items.map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n';return {required:lines([['index','field'],...v.map(r=>[r.index,r.field])]),observations:lines([['index','field','value'],...v.filter(r=>r.recorded).map(r=>[r.index,r.field,r.value])])};}
 // Array-only v1 format avoids JSON object duplicate-key ambiguity. Drafts may
 // have empty/invalid indexes or duplicates; CSV export validates separately.
 function draftRows(rows){
  if(!Array.isArray(rows)||rows.length>MAX_ROWS)throw Error('Invalid backup: too many rows or invalid row list.');
  return rows.map((r,i)=>{
   if(!Array.isArray(r)||r.length!==4)throw Error('Invalid backup row '+(i+1)+'.');
   const [index,field,recorded,value]=r;
   if(typeof index!=='string'||index.length>MAX_INDEX||/[\r\n]/.test(index)||!FIELDS.includes(field)||typeof recorded!=='boolean'||typeof value!=='string'||value.length>MAX_VALUE||value.includes('\r'))throw Error('Invalid backup row '+(i+1)+'.');
   return {index,field,recorded,value};
  });
 }
 function bundle(rows){const files=csv(rows);return JSON.stringify(['retest-evidence',1,files.required,files.observations]);}
 function backup(rows){
  if(!Array.isArray(rows))throw Error('Invalid worksheet.');
  const draft=draftRows(rows.map(r=>[r.index,r.field,r.recorded,r.value]));
  return JSON.stringify(['retest-capture',1,draft.map(r=>[r.index,r.field,r.recorded,r.value])]);
 }
 function restore(text){
  if(typeof text!=='string'||text.length>MAX_BACKUP_BYTES)throw Error('Backup is too large or invalid.');
  let data;try{data=JSON.parse(text);}catch{throw Error('Backup is not valid JSON.');}
  if(!Array.isArray(data)||data.length!==3||data[0]!=='retest-capture'||data[1]!==1)throw Error('Unsupported backup format or version.');
  return draftRows(data[2]);
 }
 return {FIELDS,MAX_ROWS,MAX_VALUE,MAX_INDEX,MAX_BACKUP_BYTES,validate,csv,bundle,backup,restore};
});
