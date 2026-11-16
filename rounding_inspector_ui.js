'use strict';
(()=>{const price=document.getElementById('price'),tick=document.getElementById('tick'),results=document.getElementById('results'),status=document.getElementById('status'),verdict=document.getElementById('verdict');
 function reset(){results.hidden=true;status.textContent='';}
 function calculate(){reset();try{const r=window.RetestRounding.compare(price.value,tick.value);document.getElementById('exact-index').textContent=r.exactTicks;document.getElementById('exact-price').textContent=r.exactPrice;document.getElementById('model-index').textContent=r.modelTicks;document.getElementById('quotient').textContent=r.quotient;verdict.classList.toggle('different',r.different);verdict.textContent=r.different?'Different tick indexes for these typed inputs. Investigate; neither result verifies Pine.':'Same tick index for these typed inputs. This is not proof of precision or parity.';results.hidden=false;}catch(e){status.textContent=e.message;}}
 price.addEventListener('input',reset);tick.addEventListener('input',reset);document.getElementById('calculate').addEventListener('click',calculate);
 function example(p,t){price.value=p;tick.value=t;calculate();}
 document.getElementById('example-near').addEventListener('click',()=>example('0.0049999999995','0.01'));document.getElementById('example-negative').addEventListener('click',()=>example('-0.005','0.01'));
})();
