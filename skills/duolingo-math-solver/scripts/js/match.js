// "Match the pairs" / Match Madness (timed). Runs as one in-page async loop, because the board is on
// a clock and a CLI round trip per click would spend it (the first manual attempt scored 1 star).
//
// Live behaviour (unit 4 level 4):
//   - cards are buttons [data-test="-challenge-tap-token"] in two columns; the value is the KaTeX
//     annotation inside each card. There is no CHECK button: the second click grades the pair.
//   - dispatched mouse events are accepted (unlike the lesson START button).
//   - a clicked card gains one class (selected); the second click of a pair clears it within ~70 ms.
//   - a matched pair is then marked in one of two ways, both seen in the same session:
//       fade:  opacity 1 -> 0 over ~2 s starting at once, then the SAME button is refilled in place
//       grey:  aria-disabled="true" after ~870 ms, opacity stays 1, the card stays until the board
//              is replaced
//     In both modes the button keeps its text until it is refilled.
// So the loop remembers the buttons it matched and skips each one until its text changes.
//
// Read-back, in two stages:
//   sync   the first click must select the card and the second must clear that selection, so the
//          game consumed exactly this pair and the click state cannot drift;
//   async  within CONFIRM_MS both cards must fade or turn aria-disabled. Waiting ~870 ms per pair
//          would halve throughput, so the loop keeps matching and checks earlier pairs on every
//          pass; the first pair that fails to confirm stops the loop with ERR.
//
// window.__duoDryRun = true     -> return the pairs for the current board, no clicks
// window.__duoMatchBudgetMs     -> how long one call may run (default 15000; eval times out at 25 s)
(async () => {
  const L = window.__duoLib;
  if (!L) return 'ERR lib-not-loaded';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const now = () => performance.now();
  const until = async (ok, ms) => { for (const t = now(); now() - t < ms; await sleep(10)) if (ok()) return true; return ok(); };
  const t0 = now(), budget = window.__duoMatchBudgetMs || 15000;
  const SELECT_MS = 300, CONSUME_MS = 400, CONFIRM_MS = 2500, GONE_MS = 2000, STUCK_MS = 4000, NOPAIR_MS = 1500;
  const fire = el => ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']
    .forEach(t => el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window })));

  const cards = () => [...document.querySelectorAll('[data-test$=challenge-tap-token]')];
  const tex = b => b.querySelector('annotation')?.textContent ?? '';
  const short = t => L.tidy(L.clean(t)).replace(/\s+/g, '');
  const opacity = b => parseFloat(getComputedStyle(b).opacity);
  const disabled = b => b.disabled || b.getAttribute('aria-disabled') === 'true';
  const x = b => b.getBoundingClientRect().x;
  // survives across calls: the budget can end while matched cards are still on the board
  const pending = window.__duoMatchPending || (window.__duoMatchPending = new WeakMap());

  const available = b => {
    if (disabled(b)) return false;
    const p = pending.get(b);
    if (p && tex(b) !== p.tex) pending.delete(b);                       // refilled in place
    else if (p && now() - p.t > STUCK_MS && opacity(b) >= 0.999) pending.delete(b);  // refilled with an identical card
    else if (p) return false;
    return opacity(b) >= 0.999;                                         // fully shown, not mid-fade
  };

  const plan = () => {
    const all = cards();
    const xs = all.map(x), mid = (Math.min(...xs) + Math.max(...xs)) / 2;
    const live = all.filter(available);
    const val = new Map(live.map(b => [b, L.texValue(tex(b))]));
    const bad = live.filter(b => val.get(b) === null);
    const left = live.filter(b => x(b) < mid && val.get(b) !== null);
    const right = live.filter(b => x(b) >= mid && val.get(b) !== null);
    const used = new Set(), pairs = [];
    for (const a of left) {
      const b = right.find(r => !used.has(r) && Math.abs(val.get(r) - val.get(a)) < 1e-9);
      if (b) { used.add(b); pairs.push({ a, b, ta: tex(a), tb: tex(b) }); }
    }
    return { all, live, bad, pairs, oneColumn: Math.max(...xs) - Math.min(...xs) < 20 };
  };
  const show = p => p.pairs.map(q => short(q.ta) + '=' + short(q.tb)).join(' ');

  // A card left selected (by a person or an aborted run) would turn our first click into a wrong
  // pair. Selection adds one class to the card; so does the grey "matched" state, hence only
  // enabled, fully shown, not-pending cards are compared. Refuse to start rather than guess.
  const idle = cards().filter(available);
  if (idle.length) {
    const freq = {};
    idle.forEach(b => { freq[b.className] = (freq[b.className] || 0) + 1; });
    const base = Object.keys(freq).sort((p, q) => freq[q] - freq[p])[0];
    const sel = idle.filter(b => b.className !== base && b.className.startsWith(base));
    if (sel.length) return 'ERR card-preselected :: ' + sel.map(b => short(tex(b))).join(' ');
  }

  if (window.__duoDryRun === true) {
    const p = plan();
    if (p.oneColumn) return 'ERR one-column';
    return 'MATCH dry-run pairs=' + p.pairs.length + ' :: ' + show(p) +
      (p.bad.length ? ' unparsed=' + JSON.stringify(p.bad.map(b => tex(b))) : '');
  }

  // Async stage of the read-back. A card that left the DOM went with the board (star break / end).
  // Refilling one card of the pair is proof on its own: an unmatched card is never refilled, and
  // the other card may come back with the same text it had (seen when a grey board is replaced
  // in the same frame as its last pair turns grey).
  const open = [];
  const marked = (b, o, t) => !b.isConnected || disabled(b) || opacity(b) < o - 1e-3 || tex(b) !== t;
  const confirmOpen = () => {
    for (let k = open.length - 1; k >= 0; k--) {
      const q = open[k];
      if ((marked(q.a, q.oa, q.ta) && marked(q.b, q.ob, q.tb)) || tex(q.a) !== q.ta || tex(q.b) !== q.tb) open.splice(k, 1);
      else if (now() - q.t > CONFIRM_MS) return 'ERR match-not-confirmed after ' + n + ' pairs :: ' + short(q.ta) + '=' + short(q.tb);
    }
    return null;
  };

  let n = 0, why = 'budget', lastSeen = now(), stallSince = null, err = null;
  const done = [];
  while (now() - t0 < budget) {
    if ((err = confirmOpen())) return err;
    const p = plan();
    if (!p.all.length) {
      if (now() - lastSeen > GONE_MS) { why = 'board-gone'; break; }
      await sleep(100); continue;
    }
    lastSeen = now();
    if (p.oneColumn) return 'ERR one-column';
    if (!p.pairs.length) {
      // Normal while matched cards wait to be refilled. With nothing pending and nothing to pair,
      // the board holds a card the solver cannot read or a pair it cannot see: stop, do not guess.
      if (p.live.length === p.all.length) {
        stallSince = stallSince ?? now();
        if (now() - stallSince > NOPAIR_MS) {
          return 'ERR no-pair after ' + n + ' pairs :: ' + JSON.stringify(p.all.map(b => tex(b))) +
            (p.bad.length ? ' unparsed=' + p.bad.length : '');
        }
      } else stallSince = null;
      await sleep(60); continue;
    }
    stallSince = null;
    for (const q of p.pairs) {
      if (tex(q.a) !== q.ta || tex(q.b) !== q.tb || !available(q.a) || !available(q.b)) break;  // re-plan
      q.oa = opacity(q.a); q.ob = opacity(q.b);
      const c0 = q.a.className;
      fire(q.a);
      if (!await until(() => q.a.className !== c0, SELECT_MS)) return 'ERR select-not-registered after ' + n + ' pairs :: ' + short(q.ta);
      const c1 = q.a.className;
      fire(q.b);
      if (!await until(() => q.a.className !== c1, CONSUME_MS)) return 'ERR pair-not-consumed after ' + n + ' pairs :: ' + short(q.ta) + '=' + short(q.tb);
      q.t = now();
      pending.set(q.a, { tex: q.ta, t: q.t }); pending.set(q.b, { tex: q.tb, t: q.t });
      open.push(q);
      n++; done.push(short(q.ta) + '=' + short(q.tb));
    }
  }
  // settle the last pairs before reporting them as matched
  await until(() => { err = confirmOpen(); return err !== null || !open.length; }, CONFIRM_MS + 200);
  if (err) return err;
  if (open.length) return 'ERR match-not-confirmed after ' + n + ' pairs :: ' + short(open[0].ta) + '=' + short(open[0].tb);
  return 'MATCH ok pairs=' + n + ' stop=' + why + ' t=' + ((now() - t0) / 1000).toFixed(1) + 's :: ' +
    done.slice(-4).join(' ');
})()
