/* Shared navigation for Paper and Ink. Direct HTML is the source of truth. */
(function () {
  'use strict';
  const stage = document.getElementById('deck-stage');
  const slides = Array.from(document.querySelectorAll('.slide'));
  const prev = document.getElementById('deck-prev');
  const next = document.getElementById('deck-next');
  const cur = document.getElementById('deck-cur');
  const total = document.getElementById('deck-total');
  const store = 'deck:idx:' + location.pathname;
  const interactive = 'a,button,input,textarea,select,summary,[contenteditable],[role="button"],[role="link"]';
  let idx = 0;
  slides.forEach(s => s.setAttribute('tabindex', '-1'));
  cur.setAttribute('aria-live', 'polite');
  cur.setAttribute('aria-atomic', 'true');
  function fit() {
    const scale = Math.max(.001, Math.min((innerWidth - 32) / 1920, (innerHeight - 32) / 1080));
    stage.style.transform = `translate(${(innerWidth - 1920 * scale) / 2}px,${(innerHeight - 1080 * scale) / 2}px) scale(${scale})`;
  }
  function go(n) {
    const focused = document.activeElement;
    idx = Math.max(0, Math.min(slides.length - 1, n));
    const restore = slides.some((s, i) => i !== idx && s.contains(focused));
    slides.forEach((s, i) => s.classList.toggle('active', i === idx));
    cur.textContent = String(idx + 1).padStart(2, '0');
    total.textContent = String(slides.length).padStart(2, '0');
    prev.disabled = idx === 0;
    next.disabled = idx === slides.length - 1;
    try { localStorage.setItem(store, String(idx)); } catch (_) {}
    history.replaceState(null, '', '#' + (idx + 1));
    if (restore) slides[idx].focus({preventScroll: true});
  }
  function hashIndex() {
    const match = /^#([1-9]\d*)$/.exec(location.hash);
    return match && +match[1] <= slides.length ? +match[1] - 1 : null;
  }
  function onKey(e) {
    if (e.__odDeckKeyHandled || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
    const t = e.target;
    if (t?.closest('input,textarea,select,summary,[contenteditable]')) return;
    // Space/Enter belong to native interactive controls, including child targets.
    if ((e.key === ' ' || e.key === 'Enter') && t?.closest(interactive)) return;
    let n;
    if (['ArrowRight', 'PageDown', ' '].includes(e.key)) n = idx + 1;
    else if (['ArrowLeft', 'PageUp'].includes(e.key)) n = idx - 1;
    else if (e.key === 'Home' || e.key.toLowerCase() === 'r') n = 0;
    else if (e.key === 'End') n = slides.length - 1;
    else return;
    e.__odDeckKeyHandled = true;
    e.preventDefault();
    go(n);
  }
  window.addEventListener('keydown', onKey, true);
  document.addEventListener('keydown', onKey, true);
  prev.addEventListener('click', () => go(idx - 1));
  next.addEventListener('click', () => go(idx + 1));
  document.addEventListener('click', e => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
    if (e.target.closest(interactive + ',.deck-counter')) return;
    slides[idx].focus({preventScroll: true});
    go(idx + (e.clientX < innerWidth / 2 ? -1 : 1));
  });
  window.addEventListener('hashchange', () => { const n = hashIndex(); if (n !== null) go(n); });
  window.addEventListener('resize', fit);
  let initial = hashIndex();
  if (initial === null) {
    try { initial = Number(localStorage.getItem(store) || 0); } catch (_) { initial = 0; }
    if (!Number.isInteger(initial)) initial = 0;
  }
  go(initial);
  fit();
})();
