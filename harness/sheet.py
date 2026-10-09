"""Contact sheet of a run: each capture of a profile as a labelled thumbnail.

usage: python -m harness.sheet RUN
"""

from __future__ import annotations

import pathlib
import sys

from PIL import Image, ImageDraw

THUMB_W = 360
COLUMNS = 3
LABEL_H = 24
GUTTER = 12
SKIP = (".diff.png", ".contrast.png")


def captures(run_dir: pathlib.Path, profile: str) -> list[pathlib.Path]:
    return sorted(p for p in (run_dir / profile).glob("*.png") if not p.name.endswith(SKIP))


def make_sheet(run_dir: pathlib.Path, profile: str) -> pathlib.Path:
    shots = captures(run_dir, profile)
    if not shots:
        raise FileNotFoundError(f"no captures in {run_dir / profile}")
    thumbs = []
    for path in shots:
        im = Image.open(path).convert("RGB")
        im = im.crop((0, 0, im.width, min(im.height, int(im.width * 1.6))))
        thumbs.append((path.stem, im.resize((THUMB_W, round(im.height * THUMB_W / im.width)))))
    cell_h = LABEL_H + max(t.height for _, t in thumbs)
    rows = -(-len(thumbs) // COLUMNS)
    out = Image.new("RGB", (GUTTER + COLUMNS * (THUMB_W + GUTTER), GUTTER + rows * (cell_h + GUTTER)), (14, 14, 18))
    draw = ImageDraw.Draw(out)
    for i, (label, im) in enumerate(thumbs):
        x = GUTTER + (i % COLUMNS) * (THUMB_W + GUTTER)
        y = GUTTER + (i // COLUMNS) * (cell_h + GUTTER)
        draw.text((x, y + 6), label, fill=(230, 230, 230))
        out.paste(im, (x, y + LABEL_H))
    path = run_dir / f"sheet-{profile}.png"
    out.save(path)
    return path


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    run = pathlib.Path(argv[0])
    for prof in sorted(d.name for d in run.iterdir() if d.is_dir()):
        print(make_sheet(run, prof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
