// Indices of selectors that match at least one element with a layout box.
(selectors) => {
  const hits = [];
  selectors.forEach((sel, i) => {
    let els;
    try { els = document.querySelectorAll(sel); } catch { return; }
    for (const el of els) if (el.getClientRects().length) { hits.push(i); break; }
  });
  return hits;
}
