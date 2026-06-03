// Accessible behaviors for demo: menu, tooltip, modal
(function(){
  // Menu
  const menuBtn = document.getElementById('menuBtn');
  const menu = document.getElementById('menu');
  const items = Array.from(menu.querySelectorAll('.ds-menu-item'));

  function openMenu() {
    menu.style.display = 'block';
    menuBtn.setAttribute('aria-expanded','true');
    // focus first item
    items[0].focus();
    document.addEventListener('mousedown', onDocClickMenu);
  }
  function closeMenu() {
    menu.style.display = 'none';
    menuBtn.setAttribute('aria-expanded','false');
    menuBtn.focus();
    document.removeEventListener('mousedown', onDocClickMenu);
  }
  function onDocClickMenu(e){ if(!menu.contains(e.target) && e.target!==menuBtn) closeMenu(); }

  menuBtn.addEventListener('click', (e)=>{
    const open = menu.style.display === 'block';
    if(open) closeMenu(); else openMenu();
  });

  menuBtn.addEventListener('keydown',(e)=>{
    if(e.key==='ArrowDown' || e.key==='Enter' || e.key===' ') { e.preventDefault(); openMenu(); }
  });

  items.forEach((it, idx)=>{
    it.addEventListener('keydown', (e)=>{
      if(e.key==='ArrowDown'){ e.preventDefault(); items[(idx+1)%items.length].focus(); }
      if(e.key==='ArrowUp'){ e.preventDefault(); items[(idx-1+items.length)%items.length].focus(); }
      if(e.key==='Escape'){ e.preventDefault(); closeMenu(); }
      if(e.key==='Enter' || e.key===' '){ e.preventDefault(); alert('Activated: '+it.textContent); closeMenu(); }
    });
    it.addEventListener('click',(e)=>{ alert('Activated: '+it.textContent); closeMenu(); });
  });

  // Tooltip (show on focus/hover)
  const tip = document.getElementById('tip');
  const tooltipBtn = document.getElementById('tooltipBtn');

  function positionTip(){
    const r = tooltipBtn.getBoundingClientRect();
    tip.style.left = (r.left + window.scrollX) + 'px';
    tip.style.top = (r.bottom + window.scrollY + 8) + 'px';
  }
  function showTip(){ positionTip(); tip.style.display='block'; }
  function hideTip(){ tip.style.display='none'; }

  tooltipBtn.addEventListener('mouseenter', showTip);
  tooltipBtn.addEventListener('mouseleave', hideTip);
  tooltipBtn.addEventListener('focus', showTip);
  tooltipBtn.addEventListener('blur', hideTip);
  window.addEventListener('resize', ()=>{ if(tip.style.display==='block') positionTip(); });

  // Modal (focus trap, escape to close)
  const openModal = document.getElementById('openModal');
  const modalBackdrop = document.getElementById('modalBackdrop');
  const cancelExport = document.getElementById('cancelExport');
  const confirmExport = document.getElementById('confirmExport');
  let lastFocused = null;

  function trapFocus(e){
    const focusable = modalBackdrop.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if(focusable.length===0) return;
    const first = focusable[0];
    const last = focusable[focusable.length-1];
    if(e.key==='Tab'){
      if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
      else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
    }
  }

  function openModalDialog(){ lastFocused = document.activeElement; modalBackdrop.style.display='flex'; const focusable = modalBackdrop.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'); if(focusable.length) focusable[0].focus(); document.addEventListener('keydown', onModalKeydown); }
  function closeModalDialog(){ modalBackdrop.style.display='none'; if(lastFocused) lastFocused.focus(); document.removeEventListener('keydown', onModalKeydown); }

  function onModalKeydown(e){ if(e.key==='Escape'){ e.preventDefault(); closeModalDialog(); } trapFocus(e); }

  openModal.addEventListener('click', openModalDialog);
  cancelExport.addEventListener('click', closeModalDialog);
  confirmExport.addEventListener('click', ()=>{ alert('Export started'); closeModalDialog(); });

})();
