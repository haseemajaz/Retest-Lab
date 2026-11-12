/* In-memory comparison of validated RetestGeometry results. No storage or network. */
(function(root){
  'use strict';
  const header='scenario,direction,entry,stop,tick,risk_distance,risk_ticks,target_number,configured_r,target_price,target_distance_ticks,effective_r_4dp,changed_by_rounding';
  function copy(r){return JSON.parse(JSON.stringify(r));}
  function createBook(){
    let items=[];
    return {
      add(result){
        if(items.length>=3) throw new Error('Comparison is full. Remove a scenario first.');
        if(!result || !Array.isArray(result.targets) || result.targets.length!==4) throw new Error('Calculate a valid example first.');
        const id=['A','B','C'].find(x=>!items.some(i=>i.id===x));
        items.push({id, result:copy(result)});return id;
      },
      remove(id){items=items.filter(x=>x.id!==id);},
      clear(){items=[];},
      replace(validated){items=copy(validated);},
      list(){return copy(items);},
      csv(){
        const rows=[header];
        items.forEach(({id,result:r})=>r.targets.forEach((price,i)=>rows.push([id,r.direction,r.entry,r.stop,r.tick,r.risk,r.riskTicks,i+1,r.rs[i],price,r.targetTicks[i],r.achievedR[i],r.roundingChanged[i]].join(','))));
        return rows.join('\r\n')+'\r\n';
      }
    };
  }
  const api={createBook};if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.RetestComparison=api;
})(typeof globalThis==='undefined'?this:globalThis);
