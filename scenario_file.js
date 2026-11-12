/* Versioned local comparison files. Imported results are recalculated, not trusted. */
(function(root){'use strict';
 const MAX_BYTES=16384;
 function serialize(items){
   if(!Array.isArray(items)||items.length<1||items.length>3)throw new Error('Save between one and three scenarios.');
   return JSON.stringify({format:'retest-lab-comparison',version:1,scenarios:items.map(({id,result:r})=>({id,direction:r.direction,entry:r.entry,stop:r.stop,tick:r.tick,rs:r.rs}))},null,2)+'\n';
 }
 function parse(text,calculate){
   if(typeof text!=='string'||new TextEncoder().encode(text).length>MAX_BYTES)throw new Error('File exceeds 16 KB or is not text.');
   let data;try{data=JSON.parse(text)}catch(e){throw new Error('This is not valid JSON.');}
   if(!data||typeof data!=='object'||Array.isArray(data)||data.format!=='retest-lab-comparison'||data.version!==1||!Array.isArray(data.scenarios)||data.scenarios.length<1||data.scenarios.length>3)throw new Error('Unsupported comparison file or scenario count.');
   const ids=new Set();return data.scenarios.map(item=>{
     if(!item||typeof item!=='object'||Array.isArray(item)||!['A','B','C'].includes(item.id)||ids.has(item.id))throw new Error('Scenario labels must be unique A, B or C.');ids.add(item.id);
     if(!['long','short'].includes(item.direction)||!['entry','stop','tick'].every(k=>typeof item[k]==='string')||!Array.isArray(item.rs)||item.rs.length!==4||!item.rs.every(v=>typeof v==='string'))throw new Error('Invalid scenario inputs.');
     try{return {id:item.id,result:calculate({direction:item.direction,entry:item.entry,stop:item.stop,tick:item.tick,rs:item.rs})}}catch(e){throw new Error('Scenario '+item.id+': '+e.message)}
   });
 }
 const api={serialize,parse,MAX_BYTES};if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.RetestScenarioFile=api;
})(typeof globalThis==='undefined'?this:globalThis);
