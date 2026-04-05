// ===== rf-nav-mobile-addon.js =====
(function(){
  // Helpers
  function q(sel, ctx){ return (ctx||document).querySelector(sel); }
  function qa(sel, ctx){ return Array.prototype.slice.call((ctx||document).querySelectorAll(sel)); }
  function isModalOpen(){
    var m = q('#reference-modal');
    if (!m) return false;
    if (m.getAttribute('aria-hidden') === 'false') return true;
    var cs = getComputedStyle(m);
    return cs.display !== 'none' && cs.visibility !== 'hidden';
  }
  function on(el, ev, fn, opts){ if(el) el.addEventListener(ev, fn, opts||false); }

  // ---- Swipe support ----
  var startX=0, startY=0, startT=0, tracking=false;
  var SWIPE_THRESH_PX = 48;   // horizontal travel needed
  var SWIPE_MAX_OFFAXIS = 60; // reject if vertical travel too big

  function touchStart(e){
    var t = e.changedTouches ? e.changedTouches[0] : e;
    startX = t.clientX; startY = t.clientY; startT = Date.now(); tracking = true;
  }
  function touchEnd(e){
    if(!tracking) return;
    var t = e.changedTouches ? e.changedTouches[0] : e;
    var dx = t.clientX - startX;
    var dy = t.clientY - startY;
    var adx = Math.abs(dx), ady = Math.abs(dy);
    tracking = false;
    if (ady > SWIPE_MAX_OFFAXIS) return;
    if (adx < SWIPE_THRESH_PX) return;
    if (dx < 0){ // swipe left -> next
      if (typeof window.rfNext === 'function') window.rfNext();
    } else {     // swipe right -> prev
      if (typeof window.rfPrev === 'function') window.rfPrev();
    }
  }

  function bindSwipe(){
    var img = q('#rf-modal-image');
    var modal = q('#reference-modal .rf-modal-wrap') || q('#reference-modal');
    // Touch devices
    on(img, 'touchstart', touchStart, {passive:true});
    on(img, 'touchend', touchEnd, {passive:true});
    on(modal, 'touchstart', touchStart, {passive:true});
    on(modal, 'touchend', touchEnd, {passive:true});
    // Mouse as a fallback (desktop testing)
    on(img, 'mousedown', touchStart);
    on(img, 'mouseup', touchEnd);
  }

  // ---- Tap hit zones (phones) ----
  var leftZone, rightZone;
  function ensureHitZones(){
    if (!leftZone){
      leftZone = document.createElement('div');
      leftZone.className = 'rf-hit rf-hit-left';
      leftZone.setAttribute('aria-hidden','true');
      leftZone.addEventListener('click', function(){ if (isModalOpen() && window.rfPrev) window.rfPrev(); });
    }
    if (!rightZone){
      rightZone = document.createElement('div');
      rightZone.className = 'rf-hit rf-hit-right';
      rightZone.setAttribute('aria-hidden','true');
      rightZone.addEventListener('click', function(){ if (isModalOpen() && window.rfNext) window.rfNext(); });
    }
    if (!leftZone.isConnected) document.body.appendChild(leftZone);
    if (!rightZone.isConnected) document.body.appendChild(rightZone);
  }

  function updateHitZones(){
    var show = isModalOpen();
    if (leftZone) leftZone.classList.toggle('show', show);
    if (rightZone) rightZone.classList.toggle('show', show);
  }

  // Observe modal open/close to toggle zones
  function installObserver(){
    var modal = q('#reference-modal');
    if (!modal) return;
    var obs = new MutationObserver(updateHitZones);
    obs.observe(modal, {attributes:true, attributeFilter:['style','aria-hidden','class']});
    updateHitZones();
  }

  function hideUI(){
  // hide arrows + tap zones and reset index
  var els = document.querySelectorAll('.rf-outer-nav');
  els.forEach(el => el.classList.remove('show'));
  if (leftZone) leftZone.classList.remove('show');
  if (rightZone) rightZone.classList.remove('show');
  window.RF_CURRENT_INDEX = -1;
}

  function init(){
    ensureHitZones();
    bindSwipe();
    installObserver();
  }
  if (document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', init); } else { init(); }
})();
