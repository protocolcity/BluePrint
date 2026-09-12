(async () => {
  const $=id=>document.getElementById(id), params=new URLSearchParams(location.search);
  const project=params.get('project') || '';let papers=[];
  async function openPaper(path, focus=true) {
    try {
      const response=await fetch('/api/document?'+new URLSearchParams({project,path}));const paper=await response.json();
      if(!response.ok)throw new Error(paper.error);
      $('paper-title').textContent=paper.title;$('paper-source').textContent=`${paper.path} · ${paper.exposure}`;
      $('paper-content').textContent=paper.content;$('paper-reader').hidden=false;
      history.replaceState(null,'','/documents?'+new URLSearchParams({project,path}));
      if(focus){$('paper-title').focus();$('paper-reader').scrollIntoView({block:'start'});}
    } catch(error){$('document-status').textContent=error.message || 'Document could not be loaded.';}
  }
  function paint() {
    const q=$('document-search').value.toLowerCase(), container=$('paper-catalog');container.replaceChildren();
    for(const layer of ['Product','System','Operations','Development']) {
      const matches=papers.filter(p=>p.layer===layer && `${p.title} ${p.path}`.toLowerCase().includes(q));
      if(!matches.length)continue;
      const section=document.createElement('section'),heading=document.createElement('h2');heading.textContent=layer;section.append(heading);
      for(const paper of matches){const link=document.createElement('a');link.className='bp-paper-row';link.href='/documents?'+new URLSearchParams({project,path:paper.path});link.textContent=paper.path;link.addEventListener('click',event=>{if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();openPaper(paper.path);});section.append(link);}
      container.append(section);
    }
    if(!container.children.length)container.textContent='No matching papers.';
  }
  $('document-search').addEventListener('input',paint);
  try {
    const response=await fetch('/api/documents?'+new URLSearchParams({project}));const data=await response.json();
    if(!response.ok)throw new Error(data.error);
    papers=data.papers;$('document-project').textContent=data.name+' · Papers';
    $('document-status').textContent=`${papers.length} existing documents${data.truncated?' · first 500 shown':''}`;paint();
    if(params.get('path'))await openPaper(params.get('path'),false);
  } catch(error){$('document-status').textContent=error.message || 'Project papers unavailable.';}
})();
