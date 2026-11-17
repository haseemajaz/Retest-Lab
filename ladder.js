/* A to-scale view of already-calculated price levels. */
(function(root){'use strict';
 function rows(r){
  if(!r||!['long','short'].includes(r.direction)||!Array.isArray(r.targets)||r.targets.length!==4)throw new Error('Calculate a valid example first.');
  const targets=r.targets.map((price,i)=>({kind:'target',label:'Target '+(i+1),price}));
  const entry={kind:'entry',label:'Entry',price:r.entry},stop={kind:'stop',label:'Stop',price:r.stop};
  return r.direction==='long'?[...targets.reverse(),entry,stop]:[stop,entry,...targets];
 }
 /* Vertical position of each level, 0 at the highest price and 100 at the
    lowest, spaced by actual price distance. Rounded to one decimal so a
    rendered chart is deterministic. The range is always the levels
    themselves, so even a one-tick setup spreads across the full chart. */
 function geometry(r){
  const list=rows(r);
  const prices=list.map(x=>Number(x.price));
  const max=Math.max.apply(null,prices),min=Math.min.apply(null,prices);
  const span=max-min;
  if(!(span>0))throw new Error('Calculate a valid example first.');
  return list.map(x=>({kind:x.kind,label:x.label,price:x.price,position:Math.round(1000*(max-Number(x.price))/span)/10}));
 }
 const api={rows,geometry};if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.RetestLadder=api;
})(typeof globalThis==='undefined'?this:globalThis);
