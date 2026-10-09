// Paint in Jellyfin's blue that a user can see: text, backgrounds, visible
// borders and outlines, SVG fills, gradients. Jellyfin's blues sit at hue 195
// to 199; the skin's teal sits at 175 and its crimson at 350.
() => {
  const rgba = (v) => {
    let m = v && v.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
    m = v && v.match(/color\(srgb ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)(?: \/ ([\d.]+))?\)/);
    if (m) return [m[1] * 255, m[2] * 255, m[3] * 255, m[4] === undefined ? 1 : +m[4]];
    return null;
  };
  const blue = (v) => {
    const c = rgba(v);
    if (!c || c[3] === 0) return false;
    const [r, g, b] = c;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    if (!d) return false;
    let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    h = (h * 60 + 360) % 360;
    return h >= 188 && h <= 206 && d / mx >= 0.6 && mx / 255 >= 0.3;
  };
  const name = (e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    [...e.classList].filter((c) => !c.startsWith('css-')).slice(0, 3).map((c) => '.' + c).join('');
  const hasText = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
  const out = {};
  for (const el of document.querySelectorAll('*')) {
    if (!el.getClientRects().length) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.opacity === '0') continue;
    const hits = [];
    if (hasText(el) && blue(cs.color)) hits.push('color');
    if (blue(cs.backgroundColor)) hits.push('background');
    for (const s of ['top', 'right', 'bottom', 'left']) {
      if (parseFloat(cs.getPropertyValue(`border-${s}-width`)) > 0 && cs.getPropertyValue(`border-${s}-style`) !== 'none'
          && blue(cs.getPropertyValue(`border-${s}-color`))) hits.push(`border-${s}`);
    }
    if (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0 && blue(cs.outlineColor)) hits.push('outline');
    if (el instanceof SVGElement && (blue(cs.fill) || blue(cs.stroke))) hits.push('svg');
    if ((cs.backgroundImage.match(/(?:rgba?|color)\([^()]*\)/g) || []).some(blue)) hits.push('gradient');
    if (hits.length) {
      const k = `${name(el)} ${hits.join(',')}`;
      out[k] = (out[k] || 0) + 1;
    }
  }
  return out;
}
