// Text elements matching the selectors that are visible in the viewport, with
// their box, colour and size: what contrast_failures samples behind.
(selectors) => {
  const rgba = (v) => {
    let m = v && v.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
    m = v && v.match(/color\(srgb ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)(?: \/ ([\d.]+))?\)/);
    if (m) return [m[1] * 255, m[2] * 255, m[3] * 255, m[4] === undefined ? 1 : +m[4]];
    return null; // a colour space this check cannot read: reported, never assumed
  };
  const name = (e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    [...e.classList].filter((c) => !c.startsWith('css-')).slice(0, 3).map((c) => '.' + c).join('');
  const out = [];
  for (const sel of selectors) {
    for (const el of document.querySelectorAll(sel)) {
      const text = (el.innerText || '').trim();
      if (!text) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1 || r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.opacity === '0') continue;
      const size = parseFloat(cs.fontSize), weight = parseInt(cs.fontWeight, 10);
      out.push({
        label: name(el), text: text.slice(0, 40), color: rgba(cs.color), raw: cs.color,
        rect: [Math.max(0, r.left), Math.max(0, r.top), Math.min(innerWidth, r.right), Math.min(innerHeight, r.bottom)],
        large: size >= 24 || (size >= 18.66 && weight >= 700),
      });
    }
  }
  return out;
}
