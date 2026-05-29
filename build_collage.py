#!/usr/bin/env python3
"""Build the 'Birds of Calvert Ct' field-guide collage.

Reads the observed-birds manifest (birds.txt) and composites the matching
illustrations from illustrations/ into a single labeled plate.

Design notes (why this looks better than a naive `montage`):
  * Birds are normalized by *content area*, not fit into a uniform square, so a
    wide perched bird and a tall upright bird carry the same visual weight.
  * Long common names wrap to two lines so every label can be set at one large,
    consistent point size.
  * A few source illustrations have a baked-in speckle/halo from a rough cutout;
    list their stems in NOISY to clean them (threshold + morphological open).

Usage:
    python3 build_collage.py                 # standard build
    python3 build_collage.py --cols 5        # override columns (default 6)

Requires ImageMagick 7 (`magick`).
"""
import os, sys, subprocess, math, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "illustrations")
MANIFEST = os.path.join(HERE, "birds.txt")
OUT = os.path.join(HERE, "birds-of-calvert-ct.png")
WORK = "/tmp/calvert-birdtiles"
MAGICK = "magick"

TITLE = "Birds of Calvert Ct"
SUBTITLE = "A field guide to our backyard flying friends"

# Source illustrations with baked-in speckle/halo that need aggressive cleanup.
# If a newly added bird shows a faint box or dotted halo, add its stem here.
NOISY = {"meleagris-gallopavo"}

# Visual tuning -- shared "field guide" look.
TARGET_AREA = 350 * 350          # every bird scaled to ~this many content px^2
BG = "#FAF7F0"                    # warm paper
LABEL_FONT = "Baskerville-SemiBold"
LABEL_COLOR = "#222018"
TITLE_FONT = "Baskerville"
TITLE_COLOR = "#2a2620"
POINTSIZE = "40"
BOX_W, BOX_H = 470, 400           # bird cell
LABEL_H, LABEL_GAP = 104, 4       # room for two lines
PAD_X, PAD_Y = 28, 26


def run(args):
    subprocess.run([str(a) for a in args], check=True, stderr=subprocess.DEVNULL)


def dims(path):
    w, h = subprocess.check_output(
        [MAGICK, "identify", "-format", "%w %h", path]).decode().split()
    return int(w), int(h)


def read_manifest():
    birds = []
    with open(MANIFEST) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "|" not in line:
                sys.exit(f"Bad manifest line (need 'Name | stem'): {raw!r}")
            name, stem = (p.strip() for p in line.split("|", 1))
            birds.append((name, stem))
    return birds


def resolve_src(stem):
    """Prefer the standing pose; fall back to the flying (-2) pose."""
    for cand in (f"{stem}.png", f"{stem}-2.png"):
        p = os.path.join(SRC, cand)
        if os.path.exists(p):
            return p
    sys.exit(f"No illustration found for stem '{stem}' in {SRC}/ "
             f"(looked for {stem}.png and {stem}-2.png)")


def make_tile(stem):
    """Area-normalized, alpha-cleaned transparent tile for one bird."""
    src = resolve_src(stem)
    w, h = dims(src)
    scale = math.sqrt(TARGET_AREA / (w * h))
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    out = os.path.join(WORK, f"tile_{stem}.png")
    if stem in NOISY:
        run([MAGICK, src, "-channel", "A", "-threshold", "50%",
             "-morphology", "Open", "Disk:3", "+channel",
             "-resize", f"{nw}x{nh}", "+repage", out])
    else:
        run([MAGICK, src, "-channel", "A", "-level", "10%,100%",
             "-morphology", "Open", "Disk:1", "+channel",
             "-resize", f"{nw}x{nh}", "+repage", out])
    return out


def make_label(text, out):
    run([MAGICK, "-background", "none", "-fill", LABEL_COLOR,
         "-font", LABEL_FONT, "-pointsize", POINTSIZE,
         "-interline-spacing", "-4", "-size", f"{BOX_W}x{LABEL_H}",
         "-gravity", "center", f"caption:{text}",
         "-extent", f"{BOX_W}x{LABEL_H}", out])


def build(cols):
    os.makedirs(WORK, exist_ok=True)
    birds = read_manifest()
    rows = math.ceil(len(birds) / cols)
    cell_w, cell_h = BOX_W, BOX_H + LABEL_GAP + LABEL_H
    cells = []
    for name, stem in birds:
        tile = make_tile(stem)
        run([MAGICK, tile, "-resize", f"{BOX_W}x{BOX_H}",
             "-background", "none", "-gravity", "center",
             "-extent", f"{BOX_W}x{BOX_H}", "+repage", f"{WORK}/_b.png"])
        make_label(name, f"{WORK}/_l.png")
        cell = f"{WORK}/cell_{stem}.png"
        run([MAGICK, "-size", f"{cell_w}x{cell_h}", "xc:none",
             f"{WORK}/_b.png", "-gravity", "north", "-geometry", "+0+0",
             "-composite",
             f"{WORK}/_l.png", "-gravity", "south", "-geometry", "+0+0",
             "-composite", cell])
        cells.append(cell)

    grid = f"{WORK}/_grid.png"
    run([MAGICK, "montage", *cells, "-tile", f"{cols}x{rows}",
         "-geometry", f"+{PAD_X}+{PAD_Y}", "-background", "none", grid])
    gw, gh = dims(grid)
    header_h = 220
    cw, ch = gw + 2 * PAD_X, gh + 2 * PAD_Y + header_h
    run([MAGICK, "-size", f"{cw}x{ch}", f"xc:{BG}",
         grid, "-gravity", "north", "-geometry", f"+0+{PAD_Y + header_h}",
         "-composite", OUT])
    run([MAGICK, OUT,
         "-font", TITLE_FONT, "-pointsize", "84", "-fill", TITLE_COLOR,
         "-gravity", "north", "-annotate", f"+0+{PAD_Y+48}", TITLE,
         "-font", LABEL_FONT, "-pointsize", "32", "-fill", TITLE_COLOR,
         "-gravity", "north", "-annotate", f"+0+{PAD_Y+165}", SUBTITLE, OUT])
    print(f"wrote {OUT} ({cw}x{ch}) with {len(birds)} birds")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cols", type=int, default=6, help="columns (default 6)")
    build(ap.parse_args().cols)
