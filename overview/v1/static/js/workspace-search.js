/* One query path for Overview and Map. Source strings never become markup. */
(() => {
  const $=id=>document.getElementById(id), input=$('workspace-query');
  if(!input)return;
  let offset=0, timer, controller, sequence=0;
  async function search() {
    const q=input.value.trim(), version=++sequence;
    controller?.abort();
    $('workspace-results').hidden=!q;
    if(!q)return;
    controller=new AbortController();
    $('workspace-search-status').textContent='Searching workspace…';
    $('workspace-search-hits').replaceChildren();
    $('workspace-search-prev').disabled=true;$('workspace-search-next').disabled=true;
    try {
      const params=new URLSearchParams({q,offset:String(offset)});
      const project=new URLSearchParams(location.search).get('project');if(project)params.set('project',project);
      const response=await fetch('/api/find?'+params,{signal:controller.signal});
      const data=await response.json();if(!response.ok)throw new Error(data.error || 'Search unavailable.');
      if(version!==sequence)return;
      $('workspace-search-status').textContent=`${data.total} matches${data.issues.length?' · Some sources incomplete':''}`;
      $('workspace-search-scope').textContent=[data.scope,...data.issues].join(' ');
      for(const hit of data.results) {
        const link=document.createElement('a');link.className='bp-paper-row';link.href=hit.href;
        const title=document.createElement('strong');title.textContent=hit.title;
        const detail=document.createElement('span');detail.className='bp-order-meta';detail.textContent=`${hit.kind} · ${hit.detail}`;
        link.append(title,detail);$('workspace-search-hits').append(link);
      }
      $('workspace-search-prev').disabled=offset===0;
      $('workspace-search-next').disabled=offset+data.limit>=data.total;
    } catch(error) {if(error.name!=='AbortError' && version===sequence)$('workspace-search-status').textContent=error.message;}
  }
  input.addEventListener('input',()=>{clearTimeout(timer);offset=0;timer=setTimeout(search,200);});
  $('workspace-search-form').addEventListener('submit',event=>{event.preventDefault();clearTimeout(timer);offset=0;search();});
  input.addEventListener('keydown',event=>{if(event.key==='Escape'){input.value='';search();}});
  $('workspace-search-prev').addEventListener('click',()=>{offset=Math.max(0,offset-50);search();});
  $('workspace-search-next').addEventListener('click',()=>{offset+=50;search();});
})();
