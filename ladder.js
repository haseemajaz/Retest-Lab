/* An ordered, not-to-scale view of already-calculated price levels. */
(function(root){'use strict';
 function rows(r){
  if(!r||!['long','short'].includes(r.direction)||!Array.isArray(r.targets)||r.targets.length!==4)throw new Error('Calculate a valid example first.');
  const targets=r.targets.map((price,i)=>({kind:'target',label:'Target '+(i+1),price}));
  const entry={kind:'entry',label:'Entry',price:r.entry},stop={kind:'stop',label:'Stop',price:r.stop};
  return r.direction==='long'?[...targets.reverse(),entry,stop]:[stop,entry,...targets];
 }
 const api={rows};if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.RetestLadder=api;
})(typeof globalThis==='undefined'?this:globalThis);
