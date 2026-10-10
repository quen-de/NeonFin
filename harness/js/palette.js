// Paint that still uses one of the given colours, on elements and their ::before and ::after:
// text, backgrounds, gradients, borders, outlines, SVG, box and text shadows. Run after
// swapping the palette, it finds any colour that did not come from a token.
(targets) => {
  const colours = (v) => {
    const out = [];
    for (const m of (v || '').matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g))
      out.push([+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]]);
    for (const m of (v || '').matchAll(/color\(srgb ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)(?: \/ ([\d.]+))?\)/g))
      out.push([m[1] * 255, m[2] * 255, m[3] * 255, m[4] === undefined ? 1 : +m[4]]);
    return out;
  };
  const stale = (v) => colours(v).some(([r, g, b, a]) => a > 0 && targets.some(([x, y, z]) =>
    Math.abs(r - x) <= 1.5 && Math.abs(g - y) <= 1.5 && Math.abs(b - z) <= 1.5));
  const name = (e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    [...e.classList].filter((c) => !c.startsWith('css-')).slice(0, 3).map((c) => '.' + c).join('');
  const out = {};
  for (const el of document.querySelectorAll('*')) {
    if (!el.getClientRects().length) continue;
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(el, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) continue;
      if (cs.visibility === 'hidden' || cs.opacity === '0') continue;
      const hits = ['color', 'backgroundColor', 'backgroundImage', 'outlineColor', 'boxShadow', 'textShadow']
        .filter((p) => stale(cs[p]));
      for (const s of ['top', 'right', 'bottom', 'left']) {
        if (parseFloat(cs.getPropertyValue(`border-${s}-width`)) > 0 && stale(cs.getPropertyValue(`border-${s}-color`))) hits.push(`border-${s}`);
      }
      if (el instanceof SVGElement && (stale(cs.fill) || stale(cs.stroke))) hits.push('svg');
      if (hits.length) {
        const k = `${name(el)}${pseudo || ''} ${hits.join(',')}`;
        out[k] = (out[k] || 0) + 1;
      }
    }
  }
  return out;
}
