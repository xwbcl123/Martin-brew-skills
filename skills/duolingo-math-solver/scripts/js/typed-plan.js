// Compute the answer for a "Type the answer" challenge.
(() => {
  const L = window.__duoLib;
  if (!L) return 'ERR lib-not-loaded';
  const prompt = L.prompt();
  if (!prompt) return 'ERR no-prompt';
  const answer = L.solveBlank(prompt);
  if (answer === null) return 'ERR no-answer :: ' + prompt;
  const input = document.querySelector('input[data-test=challenge-text-input]');
  return 'TYPED answer=' + answer + ' cur=' + (input ? JSON.stringify(input.value) : 'none') + ' prompt=' + prompt;
})()
