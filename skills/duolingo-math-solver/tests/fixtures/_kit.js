// Fixture helpers that mirror the DOM Duolingo Math actually renders: the number line and the
// tile board live in a same-origin iframe at page origin (300, 258), as measured on the live site.
window.mountFrame = function (inner) {
  const f = document.createElement('iframe');
  f.style.cssText = 'position:absolute;left:300px;top:258px;width:600px;height:600px;border:0';
  document.body.appendChild(f);
  const d = f.contentDocument;
  d.open();
  d.write('<!doctype html><body style="margin:0">' + inner + '</body>');
  d.close();
};

// ticks: label values left to right; startX/spacing: local x of the first label centre and gap.
// The thumb starts on the first tick, centred at page y = 258 + 521 + 15 = 794 like the live widget.
window.lineWidget = function (ticks, startX, spacing) {
  let h = '<div class="fixed-size number-line" style="position:relative;width:600px;height:600px">';
  ticks.forEach((v, i) => {
    const x = startX + i * spacing;
    h += '<span class="axis-label x-axis-label number-line-label" style="position:absolute;left:' + (x - 15) +
         'px;top:450px;width:30px;text-align:center">' + v + '</span>';
  });
  h += '<div class="slider1d-thumb" style="position:absolute;left:' + (startX - 15) +
       'px;top:521px;width:30px;height:30px"></div></div>';
  return h;
};

window.tilesWidget = function (nSlots, bank) {
  let h = '<div>';
  for (let i = 0; i < nSlots; i++) {
    h += '<span class="slot empty-cell" style="display:inline-block;width:50px;height:50px;margin:4px"></span>';
  }
  h += '</div><div class="token-bank">';
  bank.forEach(t => {
    h += '<div class="token-slot" style="display:inline-block;width:50px;height:50px;margin:4px">' + t + '</div>';
  });
  return h + '</div>';
};
