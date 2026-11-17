/* Retest Lab trace viewer: local structural parsing, not validation of source. */
(function(root){'use strict';
 const COLUMNS=['index','timestamp','day','state_before','state','events','cancel_reason','direction','entry','stop','t1','t2','t3','t4','fills_today','targets_hit','order_ambiguity','reject_reason'];
 const MAX_BYTES=2*1024*1024, MAX_ROWS=5000, MAX_CELL=1024;
 function parse(text){
  if(typeof text!=='string'||new TextEncoder().encode(text).length>MAX_BYTES)throw Error('File must be UTF-8 text no larger than 2 MB.');
  text=text.replace(/^\uFEFF/,''); let rows=[],row=[],cell='',state='start',i=0;
  function field(){if(cell.length>MAX_CELL)throw Error('A cell exceeds 1,024 characters.');row.push(cell);cell='';state='start';}
  function line(){field(); rows.push(row);row=[];if(rows.length>MAX_ROWS+1)throw Error('File exceeds 5,000 trace rows.');}
  while(i<text.length){let ch=text[i++];
   if(state==='quoted') {if(ch==='"'){if(text[i]==='"'){cell+='"';i++}else state='after'}else cell+=ch;}
   else if(state==='after'){if(ch===',')field();else if(ch==='\n')line();else if(ch==='\r'&&text[i]==='\n'){i++;line()}else throw Error('Unexpected character after a quoted cell.');}
   else if(ch===',')field(); else if(ch==='\n')line();else if(ch==='\r'&&text[i]==='\n'){i++;line()}else if(ch==='\r')throw Error('Use LF or CRLF line endings.');else if(ch==='"'){if(state!=='start')throw Error('Unexpected quote in an unquoted cell.');state='quoted'}else {cell+=ch;state='plain'}
   if(cell.length>MAX_CELL)throw Error('A cell exceeds 1,024 characters.');
  }
  if(state==='quoted')throw Error('Unclosed quoted cell.');
  if(state!=='start'||cell!==''||row.length)line();
  if(rows.length<2)throw Error('The trace must include a header and at least one row.');
  let header=rows.shift();if(header.length!==COLUMNS.length||new Set(header).size!==header.length||COLUMNS.some(c=>!header.includes(c)))throw Error('Expected the exact Retest Lab trace header.');
  let prev=null, output=[];
  for(let n=0;n<rows.length;n++){
   let fields=rows[n];if(fields.length!==header.length)throw Error(`Row ${n+2} has the wrong number of cells.`);
   let r=Object.create(null);header.forEach((h,j)=>r[h]=fields[j]);
   let raw=r.index.trim();if(!/^\d+$/.test(raw)||!Number.isSafeInteger(Number(raw)))throw Error(`Row ${n+2} has an invalid index.`);
   let idx=Number(raw);if(prev!==null && idx!==prev+1)throw Error(`Row ${n+2}: indexes must be consecutive and increasing.`);prev=idx;output.push(r);
  }
  return output;
 }
 function summarize(rows){
  const out={bars:rows.length,armed:0,fills:0,stops:0,targetEvents:0,eventBars:0,ambiguous:0,rejected:0,rejectReasons:{}};
  for(const r of rows){const events=r.events.trim()?r.events.split('|'):[];if(events.length)out.eventBars++;if((r.order_ambiguity||'').trim())out.ambiguous++;const rr=(r.reject_reason||'').trim();if(rr){out.rejected++;out.rejectReasons[rr]=(out.rejectReasons[rr]||0)+1;}for(const event of events){if(event==='armed_long'||event==='armed_short')out.armed++;if(event==='modeled_fill')out.fills++;if(event==='stop')out.stops++;if(/^target_[1-4]$/.test(event))out.targetEvents++;}}
  return out;
 }
 function rejectBreakdown(rows){
  const s=summarize(rows),total=s.rejected;
  return Object.entries(s.rejectReasons).map(([reason,count])=>({reason,count,share:total?count/total:0})).sort((a,b)=>b.count-a.count||(a.reason<b.reason?-1:a.reason>b.reason?1:0));
 }
 function filterRows(rows,mode){
  if(mode==='events')return rows.filter(r=>r.events.trim());
  if(mode==='rejected')return rows.filter(r=>(r.reject_reason||'').trim());
  if(mode==='ambiguous')return rows.filter(r=>(r.order_ambiguity||'').trim());
  return rows.slice();
 }
 /* Bar width for a breakdown share, in whole percent, clamped to 0–100.
    Non-finite shares draw no bar. */
 function barWidth(share){
  if(typeof share!=='number'||!isFinite(share))return 0;
  return Math.max(0,Math.min(100,Math.round(share*100)));
 }
 const api={parse,summarize,rejectBreakdown,filterRows,barWidth,COLUMNS,MAX_BYTES,MAX_ROWS};if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.RetestTraceViewer=api;
})(typeof globalThis==='undefined'?this:globalThis);
