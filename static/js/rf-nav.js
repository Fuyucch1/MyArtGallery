// ===== rf-nav-unified.patched5.js =====
(function(){
  window.__rf_unified_loaded = true;
  window.RF_VISIBLE_ITEMS = [];
  window.RF_CURRENT_INDEX = -1;

  var MOBILE_MQ = '(max-width: 1199.98px)';
  var mobileMQ = window.matchMedia(MOBILE_MQ);

  // Expose mobile flag for debugging
  window.mobileEnabled = false; // <-- globally visible
  var modalOpenFlag = false;
  var lastClickedCard = null;

  // Elements (created lazily for arrows; hit-zones exist but hidden)
  var prevBtn = null, nextBtn = null;
  var leftZone = null, rightZone = null;

  // Helpers
  function q(sel, ctx){ return (ctx||document).querySelector(sel); }
  function qa(sel, ctx){ return Array.prototype.slice.call((ctx||document).querySelectorAll(sel)); }
  function on(el, ev, fn, opts){ if(el) el.addEventListener(ev, fn, opts||false); }
  function hardHide(el){ if(el){ el.classList.remove('show'); el.style.display='none'; } }
  function hardShow(el){ if(el){ el.style.display=''; el.classList.add('show'); } }

  function isShown(el){
    if(!el) return false;
    var cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden';
  }
  function shownWithAncestors(el){
    var n = el;
    while(n && n!==document.body){
      if(!isShown(n)) return false;
      n = n.parentElement;
    }
    return true;
  }

  function rfUpdateArrows(){
    var many = window.RF_VISIBLE_ITEMS.length > 1;
    var shouldShow = modalOpenFlag && many;
    if (prevBtn && nextBtn){
      if (shouldShow){ hardShow(prevBtn); hardShow(nextBtn); }
      else { hardHide(prevBtn); hardHide(nextBtn); }
    }
    updateHitZones(shouldShow && window.mobileEnabled);
  }
  window.updateArrows = rfUpdateArrows;

  function computeVisible(){
    window.RF_VISIBLE_ITEMS = qa('.reference-item').filter(shownWithAncestors);
    rfUpdateArrows();
  }
  function norm(s){ return (s||'').split('?')[0]; }
  function cardData(card){
    var img = q('img', card);
    var src = (img && (img.getAttribute('data-original') || img.getAttribute('data-full') || img.src)) || '';
    var titleEl = card.querySelector('.ref-title');
    var name = titleEl ? (titleEl.textContent||'').trim() : (img ? (img.alt||'') : '');
    var cat = card.getAttribute('data-category') || '';
    var sub = card.getAttribute('data-subcategory') || '';
    var descEl = card.querySelector('.ref-desc');
    var desc = descEl ? (descEl.textContent || '') : '';
    return {src:src, name:name, cat:cat, sub:sub, desc:desc};
  }
  function setModalFromCard(card){
    var d = cardData(card);
    var imgEl = q('#rf-modal-image');
    var nameEl = q('#rf-modal-name');
    var catEl  = q('#rf-modal-category');
    var subEl  = q('#rf-modal-subcategory');
    var descEl = q('#rf-modal-description');
    var dlEl   = q('#rf-modal-download');
    if(imgEl) imgEl.src = d.src || '';
    if(nameEl) nameEl.textContent = d.name || ' ';
    if(catEl) catEl.textContent = d.cat ? ('Category: '+d.cat) : '';
    if(subEl) subEl.textContent = d.sub ? ('Folder: '+d.sub) : '';
    if(descEl) descEl.textContent = d.desc || 'No description available';
    if(dlEl) dlEl.href = d.src || '#';
  }
  function deriveIndexFromModal(){
    var current = norm((q('#rf-modal-image')||{}).src || '');
    for (var i=0;i<window.RF_VISIBLE_ITEMS.length;i++){
      var img = q('img', window.RF_VISIBLE_ITEMS[i]);
      var cand = norm(img && (img.getAttribute('data-original') || img.getAttribute('data-full') || img.src));
      if (cand && cand === current) return i;
    }
    return -1;
  }
  function showIndex(i){
    var list = window.RF_VISIBLE_ITEMS;
    if(!list.length) return;
    var n = list.length;
    window.RF_CURRENT_INDEX = ((i % n) + n) % n;
    setModalFromCard(list[window.RF_CURRENT_INDEX]);
    rfUpdateArrows();
  }

  // Arrows (lazy-create on first open)
  function ensureOuterArrows(){
    if (!prevBtn){
      prevBtn = document.createElement('button');
      prevBtn.type='button';
      prevBtn.className='rf-outer-nav rf-outer-prev btn btn-outline-contrast btn-no-arrow';
      prevBtn.textContent='❮';
      prevBtn.style.display='none';
      on(prevBtn, 'click', rfPrev);
      document.body.appendChild(prevBtn);
    }
    if (!nextBtn){
      nextBtn = document.createElement('button');
      nextBtn.type='button';
      nextBtn.className='rf-outer-nav rf-outer-next btn btn-outline-contrast btn-no-arrow';
      nextBtn.textContent='❯';
      nextBtn.style.display='none';
      on(nextBtn, 'click', rfNext);
      document.body.appendChild(nextBtn);
    }
  }

  // Mobile-only swipe + hit zones (create early but keep hidden)
  var startX=0, startY=0, tracking=false;
  var SWIPE_THRESH_PX = 48, SWIPE_MAX_OFFAXIS = 60;

  function ensureHitZones(){
    if (!leftZone){
      leftZone = document.createElement('div');
      leftZone.className='rf-hit rf-hit-left';
      leftZone.setAttribute('aria-hidden','true');
      leftZone.style.display='none';
      on(leftZone, 'click', function(){ if (modalOpenFlag) rfPrev(); });
      document.body.appendChild(leftZone);
    }
    if (!rightZone){
      rightZone = document.createElement('div');
      rightZone.className='rf-hit rf-hit-right';
      rightZone.setAttribute('aria-hidden','true');
      rightZone.style.display='none';
      on(rightZone, 'click', function(){ if (modalOpenFlag) rfNext(); });
      document.body.appendChild(rightZone);
    }
  }
  function updateHitZones(show){
    if (!leftZone || !rightZone) return;
    if (show){
      leftZone.style.display=''; rightZone.style.display='';
      leftZone.classList.add('show'); rightZone.classList.add('show');
      leftZone.style.top='0px'; rightZone.style.top='0px';
      var closeBtn = document.querySelector('.rf-lightbox-close');
      if (closeBtn){
        var rect = closeBtn.getBoundingClientRect();
        rightZone.style.top = Math.max(0, rect.bottom + 8) + 'px';
      }
    } else {
      leftZone.classList.remove('show'); rightZone.classList.remove('show');
      leftZone.style.display='none'; rightZone.style.display='none';
    }
  }

  function bindSwipe(){
    var img = q('#rf-modal-image');
    var wrap = q('#reference-modal .rf-modal-wrap') || q('#reference-modal');
    if (!img || !wrap) return;
    function touchStart(e){
      var t = e.changedTouches ? e.changedTouches[0] : e;
      startX=t.clientX; startY=t.clientY; tracking=true;
    }
    function touchEnd(e){
      if(!tracking) return;
      var t = e.changedTouches ? e.changedTouches[0] : e;
      var dx=t.clientX-startX, dy=t.clientY-startY;
      tracking=false;
      if (Math.abs(dy) > SWIPE_MAX_OFFAXIS) return;
      if (Math.abs(dx) < SWIPE_THRESH_PX) return;
      if (dx < 0) rfNext(); else rfPrev();
    }
    on(img, 'touchstart', touchStart, {passive:true});
    on(img, 'touchend', touchEnd, {passive:true});
    on(wrap, 'touchstart', touchStart, {passive:true});
    on(wrap, 'touchend', touchEnd, {passive:true});
    // Optional desktop emulation
    on(img, 'mousedown', touchStart);
    on(img, 'mouseup', touchEnd);
  }

  function enableMobile(){
    if (window.mobileEnabled) return;
    window.mobileEnabled = true; // expose globally
    ensureHitZones();
    bindSwipe();        // bind once; harmless if bound again
    rfUpdateArrows();   // will reveal tap zones if modal is open
  }
  function disableMobile(){
    if (!window.mobileEnabled) return;
    window.mobileEnabled = false;
    updateHitZones(false);
  }
  function handleMQ(e){
    if (e.matches) enableMobile();
    else disableMobile();
  }

  // Public navigation
  function rfNext(){
    if(window.RF_VISIBLE_ITEMS.length <= 1) return;
    if(window.RF_CURRENT_INDEX < 0) window.RF_CURRENT_INDEX = deriveIndexFromModal();
    showIndex(window.RF_CURRENT_INDEX + 1);
  }
  function rfPrev(){
    if(window.RF_VISIBLE_ITEMS.length <= 1) return;
    if(window.RF_CURRENT_INDEX < 0) window.RF_CURRENT_INDEX = deriveIndexFromModal();
    showIndex(window.RF_CURRENT_INDEX - 1);
  }
  window.rfNext = rfNext; window.rfPrev = rfPrev;

  // Hide UI & reset index
  function hideUI(){
    modalOpenFlag = false;
    hardHide(prevBtn); hardHide(nextBtn);
    updateHitZones(false);
    window.RF_CURRENT_INDEX = -1;
  }
  window.hideUI = hideUI;

  // Open/Close handling
  function handleOpened(){
    modalOpenFlag = true;
    if (!prevBtn || !nextBtn) ensureOuterArrows(); // lazy-create arrows

    window.RF_CURRENT_INDEX = -1;
    computeVisible();

    var idx=-1;
    if (lastClickedCard) idx = window.RF_VISIBLE_ITEMS.indexOf(lastClickedCard);
    if (idx < 0) idx = deriveIndexFromModal();
    window.RF_CURRENT_INDEX = idx >= 0 ? idx : 0;

    if (window.RF_VISIBLE_ITEMS[window.RF_CURRENT_INDEX]){
      setModalFromCard(window.RF_VISIBLE_ITEMS[window.RF_CURRENT_INDEX]);
    }
    lastClickedCard = null;
    rfUpdateArrows();
  }
  function handleClosed(){
    hideUI();
    rfUpdateArrows();
  }

  var modalWasOpen=false;
  function isModalActuallyOpen(){
    var m = q('#reference-modal');
    if (!m) return false;
    if (m.getAttribute('aria-hidden') === 'false') return true;
    var cs = getComputedStyle(m);
    return cs.display !== 'none' && cs.visibility !== 'hidden';
  }
  function handleModalStateChange(){
    var nowOpen = isModalActuallyOpen();
    if (nowOpen && !modalWasOpen) handleOpened();
    if (!nowOpen && modalWasOpen) handleClosed();
    modalWasOpen = nowOpen;
  }
  function installModalObserver(){
    var modal = q('#reference-modal'); if (!modal) return;
    var obs = new MutationObserver(handleModalStateChange);
    obs.observe(modal, {attributes:true, attributeFilter:['style','aria-hidden','class']});
    var bodyObs = new MutationObserver(handleModalStateChange);
    bodyObs.observe(document.body, {attributes:true, attributeFilter:['class']});

    // Close interactions
    on(document, 'keydown', function(e){ if(e.key==='Escape') hideUI(); });
    document.addEventListener('click', function(e){
      var closeBtn = e.target.closest ? e.target.closest('.rf-lightbox-close') : null;
      var modal = q('#reference-modal');
      if (closeBtn) hideUI();
      if (modal && e.target === modal) hideUI();
    }, true);

    hideUI(); // ensure hidden initially
    handleModalStateChange();
  }

  // Capture clicked card before open
  document.addEventListener('click', function(e){
    var card = e.target.closest ? e.target.closest('.reference-item') : null;
    if (card) lastClickedCard = card;
  }, true);

  function init(){
    // Remove any legacy inner arrows
    qa('#reference-modal .rf-nav').forEach(function(x){ x.remove(); });

    computeVisible();
    installModalObserver();

    // MatchMedia for mobile features — enable immediately if it matches
    handleMQ(mobileMQ);
    if (mobileMQ.addEventListener) mobileMQ.addEventListener('change', handleMQ);
    else if (mobileMQ.addListener) mobileMQ.addListener(handleMQ);

    hideUI(); // double-sure hidden
  }

  if (document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', init); }
  else { init(); }

  on(document, 'turbo:load', computeVisible);
  on(document, 'htmx:afterSettle', computeVisible);
  on(document, 'visibilitychange', function(){ if (document.hidden) hideUI(); });
})();