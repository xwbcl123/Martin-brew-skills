// Solve and select a multiple-choice challenge. Set window.__duoDryRun = true to plan without clicking.
//
// Two prompt families:
//   equation  "51 = _", "90 - 80 + 32 = _", "_ - 2 = 54"          -> solve for the blank
//   pattern   "Follow the pattern": a two-column table of rows like  225 + 25 | 250
//             with one cell "?"                                     -> evaluate the ?-cell's row partner
// A pattern table is only trusted if every complete row is an equality (left == right); anything
// else returns ERR rather than a guess.
(() => {
  const L = window.__duoLib;
  if (!L) return 'ERR lib-not-loaded';
  const fire = el => ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']
    .forEach(t => el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window })));

  const choices = [...document.querySelectorAll('[data-test=challenge-choice]')];
  if (!choices.length) return 'ERR not-a-choice-challenge';

  let target = null, how = '', detail = '';
  const prompt = L.prompt();
  if (prompt) {
    target = L.solveBlank(prompt); how = 'equation'; detail = prompt;
    if (target === null) return 'ERR choice-no-target :: ' + prompt;
  } else {
    const cells = [...document.querySelectorAll('annotation')]
      .filter(a => !a.closest('[data-test=challenge-choice]'))
      .map(a => a.textContent)
      .filter(t => !/\\textbf|\\duocursor/.test(t))
      .map(t => L.tidy(L.clean(t)));
    const q = cells.indexOf('?');
    if (q < 0) return 'ERR no-prompt :: ' + JSON.stringify(cells);
    if (cells.length % 2 !== 0) return 'ERR pattern-not-two-columns :: ' + JSON.stringify(cells);
    let complete = 0;
    for (let i = 0; i < cells.length; i += 2) {
      if (i === q || i + 1 === q) continue;
      const l = L.evalExpr(cells[i]), r = L.evalExpr(cells[i + 1]);
      if (l === null || r === null || l !== r) return 'ERR pattern-row-not-equal :: ' + cells[i] + ' | ' + cells[i + 1];
      complete++;
    }
    if (!complete) return 'ERR pattern-no-complete-row';
    const partner = cells[q ^ 1];   // same row, other column
    target = L.evalExpr(partner); how = 'pattern'; detail = partner + ' | ?';
    if (target === null) return 'ERR pattern-partner-unreadable :: ' + partner;
  }

  // Options are read from inside each choice element, so the order always matches the clickable
  // elements. Older pages are handled by the fallback: every \mathbf{} that is not the prompt.
  let opts = choices.map(c => { const a = c.querySelector('annotation'); return a ? L.tidy(L.clean(a.textContent)) : null; });
  if (opts.some(o => o === null)) {
    opts = L.annotations().filter(a => /\\mathbf\{/.test(a))
                          .filter(a => !a.includes('duoblank') && !a.includes('='))
                          .map(a => L.tidy(L.clean(a)));
  }
  if (opts.length !== choices.length) return 'ERR count-mismatch opts=' + opts.length + ' choices=' + choices.length;

  const vals = opts.map(L.evalExpr);
  const matched = vals.map((v, i) => (v === target ? i : -1)).filter(i => i >= 0);
  if (!matched.length) return 'ERR no-match :: ' + JSON.stringify({ how, target, opts, vals });

  const dry = window.__duoDryRun === true;
  if (!dry) matched.forEach(i => fire(choices[i]));
  return 'CHOICE ok ' + how + ' target=' + target + ' matched=' + matched.join(',') + (dry ? ' dry-run' : '') + ' :: ' + detail;
})()
