// Plan a number-line answer: fit x = a + b*value from the tick labels, compute the target x,
// and read the thumb back through the same mapping (the only trustworthy readback).
(() => {
  const L = window.__duoLib;
  if (!L) return JSON.stringify({ error: 'LIB_NOT_LOADED' });
  const prompt = L.prompt();
  if (!prompt) return JSON.stringify({ error: 'NO_PROMPT' });
  // the blank may be a whole side ("60 - 20 - 11 = _") or an operand ("_ - 2 = 54" -> 56)
  const target = L.solveBlank(prompt);
  if (target === null) return JSON.stringify({ error: 'NO_TARGET', prompt });

  const f = document.querySelectorAll('iframe')[0];
  if (!f || !f.contentDocument) return JSON.stringify({ error: 'NO_IFRAME' });
  const d = f.contentDocument, fr = f.getBoundingClientRect();

  const labels = [...d.querySelectorAll('.number-line-label')].map(e => {
    const r = e.getBoundingClientRect();
    return { v: Number(e.textContent.trim()), x: fr.left + r.left + r.width / 2 };
  }).filter(o => Number.isFinite(o.v)).sort((p, q) => p.v - q.v);
  if (labels.length < 2) return JSON.stringify({ error: 'NO_LABELS', n: labels.length });

  const v0 = labels[0].v, x0 = labels[0].x;
  const v1 = labels[labels.length - 1].v, x1 = labels[labels.length - 1].x;
  const b = (x1 - x0) / (v1 - v0);
  const a = x0 - b * v0;
  const targetX = a + b * target;

  // residual check: every label must sit on the fitted line
  const residuals = labels.map(L => Math.round((a + b * L.v - L.x) * 100) / 100);
  const maxResidual = Math.max(...residuals.map(Math.abs));

  const t = d.querySelector('.slider1d-thumb');
  let thumb = null;
  if (t) {
    const r = t.getBoundingClientRect();
    const cx = fr.left + r.left + r.width / 2;
    thumb = { x: Math.round(cx * 10) / 10, y: Math.round((fr.top + r.top + r.height / 2) * 10) / 10,
              value: Math.round(((cx - a) / b) * 1000) / 1000 };
  }

  return JSON.stringify({
    prompt, target,
    labelRange: [v0, v1], step: Math.round(((v1 - v0) / (labels.length - 1)) * 1000) / 1000,
    a: Math.round(a * 1000) / 1000, b: Math.round(b * 100000) / 100000,
    targetX: Math.round(targetX * 10) / 10,
    maxResidual, thumb
  });
})()
