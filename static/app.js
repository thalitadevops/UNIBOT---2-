const csrf = document.querySelector('meta[name="csrf-token"]').content;
const responseBox = document.querySelector('#response');
function el(tag, text, cls) { const node=document.createElement(tag); if(text)node.textContent=text; if(cls)node.className=cls; return node; }
async function api(path, data) {
 const res=await fetch(path, {method:data===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:data===undefined?undefined:JSON.stringify(data)});
 const body=await res.json();if(!res.ok)throw new Error(body.error||'Não foi possível concluir. Tente novamente.');return body;
}
function error(message){responseBox.replaceChildren(el('p',message,'error'));}
async function refresh(){
 const data=await api('/api/dashboard');const counts=data.counts;
 document.querySelector('#consultations').textContent=(counts.matched||0)+(counts.abstained||0);
 document.querySelector('#resolved').textContent=counts.resolved||0;document.querySelector('#tickets').textContent=counts.ticket||0;
 const list=document.querySelector('#ticket-list');list.replaceChildren();
 if(!data.tickets.length)list.append(el('p','Sua fila está vazia.','muted'));
 for(const ticket of data.tickets){const row=el('article',null,'ticket');row.append(el('strong',`#${String(ticket.id).padStart(4,'0')} · ${ticket.status}`),el('p',ticket.sector),el('small',`Prioridade: ${ticket.priority}`));list.append(row);}
}
async function outcome(value,buttons){
 buttons.querySelectorAll('button').forEach(b=>b.disabled=true);
 try{const data=await api('/api/outcome',{outcome:value});responseBox.append(el('p',value==='resolved'?'Resolução registrada. Obrigado pelo retorno.':`Chamado #${data.ticket_id} registrado na fila de demonstração. Nenhuma equipe externa foi notificada.`,'success'));await refresh();}
 catch(e){responseBox.append(el('p',e.message,'error'));}
}
async function submit(event){
 event.preventDefault();const submitButton=document.querySelector('#submit');submitButton.disabled=true;responseBox.setAttribute('aria-busy','true');responseBox.replaceChildren(el('p','Consultando a base…','muted'));
 try{
 const data=await api('/api/assist',{text:document.querySelector('#problem').value});responseBox.replaceChildren();
 responseBox.append(el('p',data.article?data.article.source:'ANÁLISE HUMANA','eyebrow'),el('h3',data.article?data.article.title:'Vamos encaminhar com cuidado.'),el('p',data.message));
 if(data.article){
  const list=el('ol');data.article.steps.forEach(step=>list.append(el('li',step)));responseBox.append(list);
  if(data.summary)responseBox.append(el('p',data.summary,'ai-summary'));
  responseBox.append(el('small',`Fonte: ${data.article.source} · Modo: ${data.mode==='ai-assisted'?'resumo por IA — confira os passos revisados':data.mode==='fallback'?'base revisada (IA indisponível)':'base revisada, sem IA generativa'}`,'muted'));
 }
 const buttons=el('div',null,'actions');
 if(data.article){const yes=el('button','Resolveu','primary');yes.type='button';yes.onclick=()=>outcome('resolved',buttons);buttons.append(yes);}
 const ticket=el('button','Abrir chamado de demonstração');ticket.type='button';ticket.onclick=()=>outcome('ticket',buttons);buttons.append(ticket);responseBox.append(buttons);await refresh();
 }catch(e){error(e.message);}finally{submitButton.disabled=false;responseBox.setAttribute('aria-busy','false');}
}
document.querySelector('#assist-form').addEventListener('submit',submit);
document.querySelectorAll('[data-query]').forEach(button=>button.addEventListener('click',()=>{document.querySelector('#problem').value=button.dataset.query;document.querySelector('#problem').focus();}));
document.querySelector('#reset').addEventListener('click',async()=>{try{await api('/api/reset',{});responseBox.replaceChildren(el('p','Demonstração limpa. Você pode começar novamente.'));await refresh();}catch(e){error(e.message);}});
refresh().catch(e=>error(e.message));
