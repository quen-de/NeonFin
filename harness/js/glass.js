// Elements (and ::before/::after) in the viewport that blur what is behind them.
() => {
  const name = (e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    [...e.classList].filter((c) => !c.startsWith('css-')).slice(0, 3).map((c) => '.' + c).join('');
  const out = [];
  for (const el of document.querySelectorAll('*')) {
    if (!el.getClientRects().length) continue;
    const r = el.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) continue;
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(el, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) continue;
      if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      const v = cs.backdropFilter || cs.webkitBackdropFilter;
      if (v && v !== 'none') out.push(name(el) + (pseudo || ''));
    }
  }
  return out;
}
