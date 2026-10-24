"""Compare two harness runs: computed styles, pixels, performance, environment."""

from __future__ import annotations

import gzip
import json
import pathlib
import sys
from collections import Counter

from PIL import Image, ImageChops


def shows_inside(key: str, *snaps: dict) -> bool:
    """Whether anything under key is visible in either run: a visible child shows inside a hidden parent."""
    prefix = key + ">"
    return any(k.startswith(prefix) and v["s"].get("visibility") != "hidden" for s in snaps for k, v in s.items())


def diff_styles(a: dict, b: dict) -> dict:
    changed = {}
    for k in a.keys() & b.keys():
        sa, sb = a[k]["s"], b[k]["s"]
        d = {p: (sa.get(p), sb.get(p)) for p in sa.keys() | sb.keys() if sa.get(p) != sb.get(p)}
        # A transform on an element hidden in both runs moves nothing anyone sees, unless a
        # visible child shows inside it. Closed MUI drawers sit there, parked by an offset
        # measured at mount that races the custom CSS.
        if "transform" in d and sa.get("visibility") == sb.get("visibility") == "hidden" and not shows_inside(k, a, b):
            d.pop("transform")
        if d:
            changed[k] = d
    return {"only_a": sorted(a.keys() - b.keys()), "only_b": sorted(b.keys() - a.keys()), "changed": changed}


def group_changes(changed: dict, labels: dict) -> list[tuple]:
    counts = Counter()
    for k, props in changed.items():
        for p, (va, vb) in props.items():
            counts[(labels.get(k, k), p, va, vb)] += 1
    return sorted(((n, *key) for key, n in counts.items()), key=lambda t: (-t[0], t[1:]))


def pixel_diff(a_png, b_png, out_png, tolerance: int = 16) -> float | None:
    a = Image.open(a_png).convert("RGB")
    b = Image.open(b_png).convert("RGB")
    if a.size != b.size:
        return None
    mask = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > tolerance else 0)
    changed = mask.histogram()[255]
    if changed:
        mask.save(out_png)
    return changed / (a.size[0] * a.size[1])


def perf_deltas(pa: dict, pb: dict) -> list[dict]:
    rows = []
    for prof in sorted(pa.keys() & pb.keys()):
        for route in sorted(pa[prof].keys() & pb[prof].keys()):
            for metric in sorted(pa[prof][route].keys() & pb[prof][route].keys()):
                ma, mb = pa[prof][route][metric], pb[prof][route][metric]
                spread = max(ma["max"] - ma["min"], mb["max"] - mb["min"])
                delta = mb["median"] - ma["median"]
                rows.append(
                    {
                        "where": f"{prof}/{route}",
                        "metric": metric,
                        "a": ma["median"],
                        "b": mb["median"],
                        "delta": round(delta, 2),
                        "significant": abs(delta) > spread,
                    }
                )
    return rows


def environment_warnings(sa: dict, sb: dict) -> list[str]:
    return [
        f"{k} differs ({sa.get(k)} vs {sb.get(k)}): diffs may come from it, not from the CSS"
        for k in ("browser_version", "server_version", "show_volatile")
        if sa.get(k) != sb.get(k)
    ]


def _load(path: pathlib.Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def compare(dir_a: pathlib.Path, dir_b: pathlib.Path) -> tuple[str, int]:
    sa = json.loads((dir_a / "summary.json").read_text())
    sb = json.loads((dir_b / "summary.json").read_text())
    lines = [f"# {dir_a.name} vs {dir_b.name}", ""]
    lines += [f"> warning: {w}" for w in environment_warnings(sa, sb)]
    names = sorted({str(p.relative_to(d)).removesuffix(".styles.json.gz") for d in (dir_a, dir_b) for p in d.glob("*/*.styles.json.gz")})
    total = 0
    for name in names:
        fa, fb = dir_a / f"{name}.styles.json.gz", dir_b / f"{name}.styles.json.gz"
        if not (fa.exists() and fb.exists()):
            lines.append(f"## {name}: only in {dir_a.name if fa.exists() else dir_b.name}")
            total += 1
            continue
        a, b = _load(fa), _load(fb)
        d = diff_styles(a, b)
        n = len(d["only_a"]) + len(d["only_b"]) + sum(len(v) for v in d["changed"].values())
        total += n
        px = pixel_diff(dir_a / f"{name}.png", dir_b / f"{name}.png", dir_b / f"{name}.diff.png")
        lines.append(f"## {name}: {n} style diffs, pixels {'size changed' if px is None else f'{px:.2%} changed'}")
        labels = {k: v["label"] for k, v in {**a, **b}.items()}
        lines += [f"- only in A: `{labels[k]}` ({k})" for k in d["only_a"][:20]]
        lines += [f"- only in B: `{labels[k]}` ({k})" for k in d["only_b"][:20]]
        lines += [f"- {c}x `{label}` {prop}: `{va}` -> `{vb}`" for c, label, prop, va, vb in group_changes(d["changed"], labels)[:50]]
    rows = perf_deltas(sa.get("perf", {}), sb.get("perf", {}))
    if rows:
        lines += ["", "## Performance (median; * = beyond trial spread)", ""]
        lines += [f"- {r['where']} {r['metric']}: {r['a']} -> {r['b']} ({r['delta']:+}){' *' if r['significant'] else ''}" for r in rows]
    return "\n".join(lines) + "\n", total


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python -m harness.compare RUN_A RUN_B", file=sys.stderr)
        return 2
    a, b = (pathlib.Path(x) for x in argv)
    report, total = compare(a, b)
    (b / f"compare-vs-{a.name}.md").write_text(report)
    print(report)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
