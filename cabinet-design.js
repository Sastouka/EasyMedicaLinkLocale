'use strict';
(()=>{
 const flow=document.querySelector('.cab-flow'), rail=flow?.querySelector('.cab-rail');
 const stopMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
 if(rail){
  const tabs=[...rail.querySelectorAll('[data-cab-step]')], panes=[...flow.querySelectorAll('[data-cab-panel]')];
  const indicator=flow.querySelector('.cab-progress span');
  function select(n,focus=false){
   tabs.forEach((tab,i)=>{
    tab.setAttribute('aria-selected',String(i===n));
    tab.tabIndex=i===n?0:-1;
    panes[i].hidden=i!==n;panes[i].classList.toggle('cab-active',i===n);
   });
   indicator.style.width=(100*(n+1)/tabs.length)+'%';
   if(focus)tabs[n].focus();
   const rect=tabs[n].getBoundingClientRect(), limits=rail.getBoundingClientRect();
   if(rect.left<limits.left||rect.right>limits.right)rail.scrollTo({left:Math.max(0,rail.scrollLeft+rect.left-limits.left-8),behavior:stopMotion.matches?'auto':'smooth'});
  }
  if(tabs.length===panes.length&&tabs.length){
   rail.setAttribute('role','tablist');flow.classList.add('cab-live');
   tabs.forEach((tab,i)=>{
    tab.setAttribute('role','tab');tab.setAttribute('aria-controls',panes[i].id);
    panes[i].setAttribute('role','tabpanel');panes[i].setAttribute('aria-labelledby',tab.id);
    tab.addEventListener('click',e=>{if(e.ctrlKey||e.metaKey||e.altKey||e.shiftKey)return;e.preventDefault();select(i)});
    tab.addEventListener('keydown',e=>{
     const n={ArrowRight:(i+1)%tabs.length,ArrowLeft:(i+tabs.length-1)%tabs.length,Home:0,End:tabs.length-1}[e.key];
     if(n!==undefined){e.preventDefault();select(n,true)}
     if(e.key===' '){e.preventDefault();select(i)}
    });
   });
   select(Math.max(0,panes.findIndex(p=>'#'+p.id===location.hash)));
  }
 }
 const d=document.querySelector('#cab-viewer');
 if(!d||typeof d.showModal!=='function')return;
 const items=[...document.querySelectorAll('[data-cab-view]')];
 const area=d.querySelector('.cab-view-area'),im=area.querySelector('img'),title=d.querySelector('h2'),zoom=d.querySelector('[data-cab-zoom]');
 let current=0,trigger;
 function open(n){
  current=(n+items.length)%items.length;
  const a=items[current];title.textContent=a.dataset.title;im.alt=a.dataset.title;im.src=a.dataset.cabSrc;
  area.classList.remove('cab-zoom');zoom.setAttribute('aria-pressed','false');area.scrollTo(0,0);
 }
 items.forEach((item,i)=>item.addEventListener('click',e=>{if(e.ctrlKey||e.metaKey||e.altKey||e.shiftKey)return;e.preventDefault();trigger=item;open(i);d.showModal()}));
 d.querySelector('[data-cab-close]').onclick=()=>d.close();
 d.querySelector('[data-cab-prev]').onclick=()=>open(current-1);
 d.querySelector('[data-cab-next]').onclick=()=>open(current+1);
 zoom.onclick=()=>zoom.setAttribute('aria-pressed',String(area.classList.toggle('cab-zoom')));
 d.addEventListener('click',e=>{if(e.target===d)d.close()});
 d.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')open(current-1);if(e.key==='ArrowRight')open(current+1)});
 d.addEventListener('close',()=>{im.removeAttribute('src');trigger?.focus()});
})();
