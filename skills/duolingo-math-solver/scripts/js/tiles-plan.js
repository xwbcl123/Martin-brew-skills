// Plan a tile equation: depth-first search over the token bank for n op n op ... = target.
(() => {
  const L = window.__duoLib;
  if (!L) return 'ERR lib-not-loaded';
  const eqRaw = L.annotations().find(a => /\\mathbf\{/.test(a) && a.includes('='));
  if (!eqRaw) return 'ERR no-equation';
  const eq = L.tidy(L.clean(eqRaw));
  // "9 = _": the blank stands for the whole tile expression
  const target = L.solveBlank(eq);
  if (target === null) return 'ERR no-target :: ' + eq;

  const f = document.querySelectorAll('iframe')[0];
  if (!f || !f.contentDocument) return 'ERR no-iframe';
  const d = f.contentDocument;

  const nSlots = d.querySelectorAll('.slot').length;
  if (!nSlots) return 'ERR no-slots';
  const bank = [...d.querySelectorAll('.token-slot')].map(e => (e.textContent || '').trim()).filter(t => t !== '');
  if (!bank.length) return 'ERR empty-bank';

  const nums = bank.filter(t => /^-?\d+$/.test(t)).map(Number);
  const ops  = bank.filter(t => t === '-' || t === '+');

  // expression shape n op n op n ... ; leading number is required
  const nNums = Math.ceil(nSlots / 2);
  const nOps  = nSlots - nNums;
  if (nNums > nums.length || nOps > ops.length) return 'ERR not-enough-tokens';

  const evalSeq = s => { let acc = s[0]; for (let i = 1; i < s.length; i += 2) acc = s[i] === '-' ? acc - s[i + 1] : acc + s[i + 1]; return acc; };

  const usedN = new Array(nums.length).fill(false);
  const usedO = new Array(ops.length).fill(false);
  const seq = [];
  let found = null;

  const dfs = () => {
    if (found) return;
    if (seq.length === nSlots) { if (evalSeq(seq) === target) found = seq.slice(); return; }
    if (seq.length % 2 === 0) {
      for (let i = 0; i < nums.length && !found; i++) {
        if (usedN[i]) continue;
        usedN[i] = true; seq.push(nums[i]); dfs(); seq.pop(); usedN[i] = false;
      }
    } else {
      for (let i = 0; i < ops.length && !found; i++) {
        if (usedO[i]) continue;
        usedO[i] = true; seq.push(ops[i]); dfs(); seq.pop(); usedO[i] = false;
      }
    }
  };
  dfs();
  if (!found) return 'ERR no-solution eq=' + eq + ' bank=[' + bank.join(' ') + '] slots=' + nSlots;

  return 'TILES target=' + target + ' seq=' + found.join(',') + ' slots=' + nSlots;
})()
