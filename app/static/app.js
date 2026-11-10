const $ = s => document.querySelector(s);
let token = sessionStorage.getItem("ns_token") || "";
let activeLead = null;
const auth = () => ({ "Content-Type":"application/json", "Authorization":`Bearer ${token}` });
async function api(url, options={}) {
  const response = await fetch(url,{...options,headers:{...auth(),...(options.headers||{})}});
  if(response.status===401){logout();throw new Error("Сессия завершена. Войдите снова.");}
  const data = await response.json();
  if(!response.ok) throw new Error(data.detail || "Ошибка запроса");
  return data;
}
function showApp(){ $("#login").classList.toggle("hidden",!!token); $("#app").classList.toggle("hidden",!token); if(token) refresh(); }
function logout(){token="";sessionStorage.removeItem("ns_token");showApp();}
$("#loginForm").addEventListener("submit",async e=>{e.preventDefault();$("#loginError").textContent="";try{const r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:$("#password").value})});const d=await r.json();if(!r.ok)throw Error(d.detail);token=d.access_token;sessionStorage.setItem("ns_token",token);$("#password").value="";showApp();}catch(err){$("#loginError").textContent=err.message;}});
$("#logout").onclick=logout;
async function refresh(){try{const [leads,stats]=await Promise.all([api("/api/leads"),api("/api/stats")]);Object.entries(stats).forEach(([k,v])=>$("#"+k).textContent=v);render(leads);}catch(e){alert(e.message);}}
function render(leads){const q=$("#search").value.toLowerCase();const filtered=leads.filter(x=>[x.name,x.phone,x.product].join(" ").toLowerCase().includes(q));$("#leads").innerHTML=filtered.map(x=>`<tr><td><strong>${esc(x.name)}</strong><small>${esc(x.phone)}</small></td><td><strong>${esc(x.product)}</strong><small>${esc(x.volume||"Объём не указан")}</small></td><td>${esc(x.source)}</td><td><select data-status="${x.id}" aria-label="Статус заявки"><option ${x.status==="Новая"?"selected":""}>Новая</option><option ${x.status==="В работе"?"selected":""}>В работе</option><option ${x.status==="Успешно"?"selected":""}>Успешно</option><option ${x.status==="Отказ"?"selected":""}>Отказ</option></select></td><td><div class="row-actions"><button data-ai="${x.id}">AI-ответ</button><button class="secondary" data-del="${x.id}">Удалить</button></div></td></tr>`).join("");$("#empty").classList.toggle("hidden",filtered.length>0);}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
$("#leads").addEventListener("change",async e=>{if(e.target.dataset.status){try{await api(`/api/leads/${e.target.dataset.status}`,{method:"PATCH",body:JSON.stringify({status:e.target.value})});refresh();}catch(err){alert(err.message);}}});
$("#leads").addEventListener("click",async e=>{const ai=e.target.dataset.ai,del=e.target.dataset.del;if(ai){activeLead=Number(ai);$("#aiPanel").classList.remove("hidden");$("#reply").value="";$("#aiPanel").scrollIntoView({behavior:"smooth"});}if(del&&confirm("Удалить заявку?")){await api(`/api/leads/${del}`,{method:"DELETE"});refresh();}});
$("#addToggle").onclick=()=>$("#leadFormWrap").classList.toggle("hidden");
$("#cancelAdd").onclick=()=>$("#leadFormWrap").classList.add("hidden");
$("#leadForm").addEventListener("submit",async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{await api("/api/leads",{method:"POST",body:JSON.stringify(data)});e.target.reset();$("#leadFormWrap").classList.add("hidden");refresh();}catch(err){alert(err.message);}});
$("#search").addEventListener("input",async()=>{const leads=await api("/api/leads");render(leads);});
$("#generate").onclick=async()=>{try{const d=await api("/api/ai/reply",{method:"POST",body:JSON.stringify({lead_id:activeLead,tone:$("#tone").value})});$("#reply").value=d.reply;}catch(e){alert(e.message);}};
$("#copy").onclick=async()=>{if($("#reply").value){await navigator.clipboard.writeText($("#reply").value);$("#copy").textContent="Скопировано";setTimeout(()=>$("#copy").textContent="Копировать",1400);}};
$("#closeAI").onclick=()=>$("#aiPanel").classList.add("hidden");
showApp();
