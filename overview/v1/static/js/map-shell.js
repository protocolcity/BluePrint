/* Map shares the operations shell, while its navigation remains local. */
(async()=>{
  const name=document.getElementById('desk-name'), path=document.getElementById('scope-path');
  document.getElementById('refresh')?.addEventListener('click',()=>location.reload());
  try {
    const response=await fetch('/api/operations');if(!response.ok)throw new Error();
    const data=await response.json();name.textContent=data.workspace?.name+' · Local';path.textContent=data.workspace?.path || 'No workspace selected.';
  } catch(error) {name.textContent='Workspace unavailable';path.textContent='Could not verify the selected workspace.';}
})();
