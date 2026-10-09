// Computed-style snapshot of every element that has a layout box, plus
// ::before/::after when they generate content. Keys are paths that start at
// the nearest ancestor with a stable id (else <body>); each step counts only
// siblings of the same tag and first class, so lazily mounted portals and
// plugin nodes do not renumber their neighbours. The full class list goes in
// the label only, because trailing classes change with state.
({ props, volatile }) => {
  const skip = new Set();
  for (const sel of volatile) for (const el of document.querySelectorAll(sel)) skip.add(el);
  const skipped = (el) => { for (let e = el; e; e = e.parentElement) if (skip.has(e)) return true; return false; };
  // Generated ids (React useId, MUI counters, item ids) are not stable.
  const stableId = (e) => !!e.id && /^[A-Za-z][\w-]*$/.test(e.id) && !/\d{3,}|^mui-/.test(e.id)
    && document.querySelectorAll('#' + CSS.escape(e.id)).length === 1;
  const kind = (e) => {
    const first = typeof e.className === 'string' ? e.className.trim().split(/\s+/)[0] : '';
    return e.tagName.toLowerCase() + (first ? '.' + first : '');
  };
  const keyOf = (el) => {
    const parts = [];
    for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
      if (stableId(e)) { parts.push('#' + e.id); break; }
      const k = kind(e);
      let i = 1;
      for (let s = e.previousElementSibling; s; s = s.previousElementSibling) if (kind(s) === k) i++;
      parts.push(`${k}:${i}`);
    }
    return parts.reverse().join('>');
  };
  const pick = (cs) => { const o = {}; for (const p of props) o[p] = cs.getPropertyValue(p); return o; };
  const out = {};
  for (const el of [document.body, ...document.body.querySelectorAll('*')]) {
    if (el.getClientRects().length === 0 || skipped(el)) continue;
    const key = keyOf(el);
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean).slice(0, 3) : [];
    const label = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + cls.map((c) => '.' + c).join('');
    out[key] = { label, s: pick(getComputedStyle(el)) };
    for (const pseudo of ['::before', '::after']) {
      const pcs = getComputedStyle(el, pseudo);
      if (pcs.content && pcs.content !== 'none' && pcs.content !== 'normal') {
        out[key + pseudo] = { label: label + pseudo, s: pick(pcs) };
      }
    }
  }
  return out;
}
