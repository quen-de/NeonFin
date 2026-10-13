// Every colour each visible element paints, ::before and ::after included, by element and
// property: text colour only where text is drawn, borders only where they show, fills on SVG.
// Run twice, once with the palette swapped, it tells colours the palette moves from the rest.
() => {
  const own = (e) => e.tagName.toLowerCase() + (e.id && !/\d{3}/.test(e.id) ? '#' + e.id : '') +
    [...e.classList].filter((c) => !c.startsWith('css-') && !/^\d/.test(c)).slice(0, 3).map((c) => '.' + c).join('') +
    (e.classList.contains('material-icons') ? `[${e.textContent.trim()}]` : '');
  const sig = (e) => (e.parentElement ? own(e.parentElement) + ' > ' : '') + own(e);
  const texty = (e) => e.classList.contains('material-icons') || [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
  const out = {};
  for (const e of document.querySelectorAll('body *')) {
    const r = e.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(e, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) continue;
      if (cs.visibility === 'hidden' || cs.opacity === '0' || cs.display === 'none') continue;
      const paint = { bg: cs.backgroundColor, shadow: cs.boxShadow };
      if (!cs.backgroundImage.includes('url(')) paint.bgimg = cs.backgroundImage;
      if (e instanceof SVGElement) { paint.fill = cs.fill; paint.stroke = cs.stroke; }
      else if (pseudo ? /^["'].+["']$/.test(cs.content) : texty(e)) paint.color = cs.color;
      if (e.tagName === 'INPUT') paint.accent = cs.accentColor;
      for (const s of ['top', 'right', 'bottom', 'left']) {
        if (parseFloat(cs.getPropertyValue(`border-${s}-width`)) > 0 && cs.getPropertyValue(`border-${s}-style`) !== 'none')
          paint.border = cs.getPropertyValue(`border-${s}-color`);
      }
      for (const [p, v] of Object.entries(paint)) {
        if (!v || v === 'none' || v === 'auto') continue;
        (out[`${sig(e)}${pseudo || ''} ${p}`] ||= new Set()).add(v);
      }
    }
  }
  return Object.fromEntries(Object.entries(out).map(([k, v]) => [k, [...v]]));
}
