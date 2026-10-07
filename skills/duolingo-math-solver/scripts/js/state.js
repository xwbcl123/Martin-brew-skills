// Classify the current challenge. Number-line and tile widgets live in a same-origin iframe,
// so main-document queries alone would miss them.
(() => {
  // "Match the pairs" / Match Madness cards are data-test="-challenge-tap-token" (leading dash).
  if (document.querySelector('[data-test$=challenge-tap-token]')) return 'MATCH';
  if (document.querySelectorAll('[data-test=challenge-choice]').length) return 'CHOICE';
  const f = document.querySelectorAll('iframe')[0];
  const d = f && f.contentDocument;
  if (d && d.querySelector('.slider1d-thumb')) return 'LINE';
  if (d && d.querySelector('.slot') && d.querySelector('.token-slot')) return 'TILES';
  if (document.querySelector('input[data-test=challenge-text-input]')) return 'TYPED';
  return 'OTHER';
})()
