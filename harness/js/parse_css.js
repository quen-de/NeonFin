// Parse CSS without applying it. Returns the style-rule count and each rule's
// selector with dynamic pseudo-classes and pseudo-elements stripped, so a
// :hover or ::before rule is tested against the element it styles.
// Ported from docs/audit.js.
(text) => {
  const testable = (sel) => sel.split(',').map((p) => p.trim()
      .replace(/::?(before|after|placeholder|selection|marker|backdrop|-webkit-[a-z-]+|-moz-[a-z-]+)(\([^)]*\))?/g, '')
      .replace(/::[a-zA-Z-]+(\([^)]*\))?/g, '')
      .replace(/:(hover|focus-within|focus-visible|focus|active|visited|target|placeholder-shown|checked|disabled|indeterminate)(?![\w-])/g, ''))
    .filter(Boolean).join(',');
  const style = document.createElement('style');
  style.media = 'not all';
  style.textContent = text;
  document.head.appendChild(style);
  const selectors = [];
  let rules = 0;
  (function walk(list) {
    for (const r of list) {
      if (r instanceof CSSStyleRule) {
        rules++;
        const t = testable(r.selectorText);
        if (t) selectors.push(t);
        if (r.cssRules && r.cssRules.length) walk(r.cssRules);
      } else if (r.cssRules && !(r instanceof CSSKeyframesRule)) {
        walk(r.cssRules);
      }
    }
  })(style.sheet.cssRules);
  style.remove();
  return { rules, selectors };
}
