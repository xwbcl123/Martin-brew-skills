// Shared prompt parsing, evaluated in front of every planner (see evfile in run.sh).
// Assigning a window property, rather than declaring top-level consts, keeps repeated evals in the
// same page from colliding.
window.__duoLib = (() => {
  const clean = s => s.replace(/\\mathbf\{/g, '').replace(/\\duoblank\{[^}]*\}/g, '_').replace(/\}/g, '');
  const tidy = s => s.replace(/\s+/g, ' ').trim();

  const evalExpr = e => {
    const s = e.replace(/−/g, '-').replace(/×/g, '*').replace(/÷/g, '/');
    if (!/^[0-9+\-*/(). ]+$/.test(s)) return null;
    try { const v = Function('"use strict";return (' + s + ')')(); return Number.isFinite(v) ? v : null; }
    catch { return null; }
  };

  // Solve "<left> = <right>" for its single blank "_". The blank may be a whole side
  // ("51 = _", "_ = 11 - 7 - 1") or an operand ("_ - 2 = 54", "100 - _ = 54"). Add/subtract
  // prompts are linear in the blank, so two probes give the slope; the answer is then substituted
  // back, and anything that does not check out returns null instead of a plausible wrong number.
  const solveBlank = prompt => {
    const sides = prompt.split('=').map(s => s.trim());
    if (sides.length !== 2) return null;
    const i = sides.findIndex(s => s.includes('_'));
    if (i < 0 || sides[1 - i].includes('_')) return null;
    const v = evalExpr(sides[1 - i]);
    if (v === null) return null;
    const f = x => evalExpr(sides[i].replace('_', '(' + x + ')'));
    const f0 = f(0), f1 = f(1);
    if (f0 === null || f1 === null || f1 === f0) return null;
    let x = (v - f0) / (f1 - f0);
    if (Math.abs(x - Math.round(x)) < 1e-9) x = Math.round(x);
    const back = f(x);
    return back !== null && Math.abs(back - v) < 1e-9 ? x : null;
  };

  // Value of a standalone TeX card such as "\mathbf{6 + 3}", "\mathbf{\frac{1}{2}}" or
  // "\mathbf{4 \times 3}". Anything else (images, words, clocks) is null, never a guess.
  const texValue = tex => {
    const s = tex.replace(/\\(?:d|t)?frac\{([^{}]*)\}\{([^{}]*)\}/g, '(($1)/($2))')
                 .replace(/\\times|\\cdot/g, '*').replace(/\\div/g, '/');
    return evalExpr(tidy(clean(s)));
  };

  const annotations = () => [...document.querySelectorAll('annotation')].map(a => a.textContent);
  const prompt = () => {
    const raw = annotations().find(a => a.includes('=') && a.includes('duoblank'));
    return raw ? tidy(clean(raw)) : null;
  };

  return { clean, tidy, evalExpr, texValue, solveBlank, annotations, prompt };
})();
