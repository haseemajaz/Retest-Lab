/* Educational comparison of a reference rounding step, not a Pine test. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.RetestRounding=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const SCALE=10n**16n, LIMIT=2n**40n;
 function parse(raw,name,maxDecimals){
  if(typeof raw!=='string')throw Error(name+': enter a decimal.');
  if(raw.length>64)throw Error(name+': input is too long.');
  const s=raw.trim(), match=/^(-?)([0-9]{1,12})(?:\.([0-9]+))?$/.exec(s);
  if(!match||(match[3]||'').length>maxDecimals)throw Error(name+': use up to 12 whole digits and '+maxDecimals+' decimal places; no exponent.');
  const mag=BigInt(match[2])*SCALE+BigInt(((match[3]||'')+'0'.repeat(16)).slice(0,16));
  return match[1]? -mag:mag;
 }
 function floorDiv(a,b){let q=a/b,r=a%b;if(r<0n)q-=1n;return q;}
 function display(v){const negative=v<0n;if(negative)v=-v;const w=v/SCALE, f=(v%SCALE).toString().padStart(16,'0').replace(/0+$/,'');return (negative?'-':'')+w.toString()+(f?'.'+f:'');}
 function compare(price,tick){
  const p=parse(price,'Price',16), t=parse(tick,'Tick',10);
  if(t<=0n)throw Error('Tick: must be greater than zero.');
  if((p<0n?-p:p)>t*LIMIT)throw Error('Price/tick ratio exceeds the supported 2^40-tick limit.');
  const exact=floorDiv(2n*p+t,2n*t); // nearest, ties toward positive infinity
  const quotient=Number(price.trim())/Number(tick.trim());
  const model=Math.floor(quotient+0.5+1e-10);
  if(!Number.isSafeInteger(model))throw Error('Floating tick index is outside the supported range.');
  return {exactTicks:exact.toString(),modelTicks:String(model),exactPrice:display(exact*t),quotient:String(quotient),different:BigInt(model)!==exact};
 }
 return {compare};
});
