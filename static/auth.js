const csrf=document.querySelector('meta[name="csrf-token"]').content;
async function post(url,data){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(data)});if(!r.ok)throw new Error('Acesso não autorizado ou limite de tentativas.');location.href='/admin';}
const form=document.querySelector('#login');if(form)form.addEventListener('submit',async e=>{e.preventDefault();try{await post('/api/login',{password:document.querySelector('#password').value});}catch(error){document.querySelector('#message').textContent=error.message;}});
const logout=document.querySelector('#logout');if(logout)logout.addEventListener('click',()=>post('/api/logout',{}));
