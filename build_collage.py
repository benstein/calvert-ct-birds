#!/usr/bin/env python3
"""Build the 'Birds of Calvert Ct' field-guide collages, sized for printing.

Reads the observed-birds manifest (birds.txt) and composites the matching
illustrations from illustrations/ into labeled plates laid out for US Letter
(8.5x11) paper in landscape, at 300 dpi.

Outputs (all landscape, 3300x2550 = 11x8.5in @300dpi):
  birds-of-calvert-ct.png         Design 1 - every bird on one sheet.
  birds-of-calvert-ct-page1.png   Design 2, top sheet - title + first half, larger.
  birds-of-calvert-ct-page2.png   Design 2, bottom sheet - second half, no title.
  birds-of-calvert-ct-2page.png   Page 1 stacked over page 2, to preview the tape-up.

Design 2 is two sheets you print and tape together top-to-bottom; with only half
the birds per sheet they're scaled up for legibility. Page 1 carries the title;
page 2 omits it so it reads as a continuation. Both pages use the same bird
scale so the taped result looks like one continuous guide.

Design notes (why this looks better than a naive `montage`):
  * Birds are normalized by *content area*, not fit into a uniform square, so a
    wide perched bird and a tall upright bird carry the same visual weight.
  * Each sheet's image aspect equals the paper's, so it scales to fill the page.
  * Long common names wrap to two lines so every label can be set at one large,
    consistent point size.
  * A few source illustrations have a baked-in speckle/halo from a rough cutout;
    list their stems in NOISY to clean them (threshold + morphological open).

Birds display alphabetically by common name (sorted at build time), so lines in
birds.txt can be added in any order.

Usage:
    python3 build_collage.py             # both designs (all four outputs)
    python3 build_collage.py --design 1  # just the single-sheet collage
    python3 build_collage.py --design 2  # just the tape-up pair (+ preview)

Requires ImageMagick 7 (`magick`).
"""
import os, sys, subprocess, math, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "illustrations")
MANIFEST = os.path.join(HERE, "birds.txt")
OUT = os.path.join(HERE, "birds-of-calvert-ct.png")
OUT_P1 = os.path.join(HERE, "birds-of-calvert-ct-page1.png")
OUT_P2 = os.path.join(HERE, "birds-of-calvert-ct-page2.png")
OUT_2UP = os.path.join(HERE, "birds-of-calvert-ct-2page.png")
WORK = "/tmp/calvert-birdtiles"
MAGICK = "magick"

TITLE = "Birds of Calvert Ct"
SUBTITLE = "A field guide to our backyard flying friends"

# Source illustrations with baked-in speckle/halo that need aggressive cleanup.
# If a newly added bird shows a faint box or dotted halo, add its stem here.
NOISY = {"meleagris-gallopavo"}

# --- Page geometry: US Letter landscape at 300 dpi -------------------------
PAGE_W, PAGE_H = 3300, 2550      # 11 x 8.5 inches
OUTER = 50                       # paper margin inside the canvas
HEADER_H = 340                   # title band height on titled sheets
CELL_GAP = 16                    # transparent margin around each bird cell
LABEL_GAP = 6                    # gap between a bird and its label
FILL = 0.60                      # bird content area as a fraction of its box

# --- The shared "field guide" look -----------------------------------------
BG = "#FAF7F0"                   # warm paper
LABEL_FONT = "Baskerville-SemiBold"
LABEL_COLOR = "#222018"
TITLE_FONT = "Baskerville"
TITLE_COLOR = "#2a2620"
TITLE_PT = 118
SUBTITLE_PT = 46


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


def make_tile(stem, target_area, out):
    """Area-normalized, alpha-cleaned transparent tile for one bird."""
    src = resolve_src(stem)
    w, h = dims(src)
    scale = math.sqrt(target_area / (w * h))
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    if stem in NOISY:
        run([MAGICK, src, "-channel", "A", "-threshold", "50%",
             "-morphology", "Open", "Disk:3", "+channel",
             "-resize", f"{nw}x{nh}", "+repage", out])
    else:
        run([MAGICK, src, "-channel", "A", "-level", "10%,100%",
             "-morphology", "Open", "Disk:1", "+channel",
             "-resize", f"{nw}x{nh}", "+repage", out])
    return out


def make_label(text, pointsize, box_w, label_h, out):
    run([MAGICK, "-background", "none", "-fill", LABEL_COLOR,
         "-font", LABEL_FONT, "-pointsize", str(pointsize),
         "-interline-spacing", "-4", "-size", f"{box_w}x{label_h}",
         "-gravity", "center", f"caption:{text}",
         "-extent", f"{box_w}x{label_h}", out])


def build_layout(birds, cols, rows, show_title, pointsize, label_h, out,
                 target_area=None):
    """Composite `birds` into a cols x rows grid filling one landscape sheet.

    Returns the bird content-area used, so a paired sheet can reuse it and keep
    a consistent scale.
    """
    os.makedirs(WORK, exist_ok=True)
    header_h = HEADER_H if show_title else 0
    grid_w = PAGE_W - 2 * OUTER
    grid_h = PAGE_H - 2 * OUTER - header_h
    cell_w, cell_h = grid_w // cols, grid_h // rows
    box_w = cell_w - 2 * CELL_GAP
    bird_h = cell_h - 2 * CELL_GAP - label_h - LABEL_GAP
    if target_area is None:
        target_area = round(FILL * box_w * bird_h)

    cells = []
    for i, (name, stem) in enumerate(birds):
        tile = make_tile(stem, target_area, f"{WORK}/tile_{i}.png")
        # Fit the area-normalized tile inside the bird box (clamps tall/wide ones).
        run([MAGICK, tile, "-resize", f"{box_w}x{bird_h}",
             "-background", "none", "-gravity", "center",
             "-extent", f"{box_w}x{bird_h}", "+repage", f"{WORK}/_b.png"])
        make_label(name, pointsize, box_w, label_h, f"{WORK}/_l.png")
        cell = f"{WORK}/cell_{i}.png"
        run([MAGICK, "-size", f"{cell_w}x{cell_h}", "xc:none",
             f"{WORK}/_b.png", "-gravity", "north", "-geometry", f"+0+{CELL_GAP}",
             "-composite",
             f"{WORK}/_l.png", "-gravity", "south", "-geometry", f"+0+{CELL_GAP}",
             "-composite", cell])
        cells.append(cell)

    grid = f"{WORK}/_grid.png"
    run([MAGICK, "montage", *cells, "-tile", f"{cols}x{rows}",
         "-geometry", f"{cell_w}x{cell_h}+0+0", "-background", "none", grid])
    gw, gh = dims(grid)
    x = (PAGE_W - gw) // 2
    y = OUTER + header_h + (grid_h - gh) // 2
    run([MAGICK, "-size", f"{PAGE_W}x{PAGE_H}", f"xc:{BG}",
         grid, "-geometry", f"+{x}+{y}", "-composite", out])
    if show_title:
        run([MAGICK, out,
             "-font", TITLE_FONT, "-pointsize", TITLE_PT, "-fill", TITLE_COLOR,
             "-gravity", "north", "-annotate", f"+0+{OUTER + 30}", TITLE,
             "-font", LABEL_FONT, "-pointsize", SUBTITLE_PT, "-fill", TITLE_COLOR,
             "-gravity", "north", "-annotate", f"+0+{OUTER + 30 + TITLE_PT + 28}",
             SUBTITLE, out])
    print(f"wrote {out} ({PAGE_W}x{PAGE_H}) - {len(birds)} birds, {cols}x{rows}")
    return target_area


def build_one_page(birds):
    """Design 1: every bird on one landscape sheet."""
    cols = 6
    build_layout(birds, cols, math.ceil(len(birds) / cols),
                 show_title=True, pointsize=40, label_h=104, out=OUT)


def build_two_page(birds):
    """Design 2: two landscape sheets to tape top-to-bottom, half the birds each."""
    half = (len(birds) + 1) // 2
    top, bottom = birds[:half], birds[half:]
    cols = 5
    # Page 1 sets the bird scale; page 2 reuses it so the taped seam is seamless.
    ta = build_layout(top, cols, math.ceil(len(top) / cols),
                      show_title=True, pointsize=54, label_h=150, out=OUT_P1)
    build_layout(bottom, cols, math.ceil(len(bottom) / cols),
                 show_title=False, pointsize=54, label_h=150, out=OUT_P2,
                 target_area=ta)
    # Stacked preview of the taped-up poster (for review, not printing).
    run([MAGICK, "-background", BG, OUT_P1, OUT_P2, "-append", OUT_2UP])
    print(f"wrote {OUT_2UP} (stacked preview of the two-sheet poster)")


def main(design):
    birds = read_manifest()
    birds.sort(key=lambda nb: nb[0].lower())   # display alphabetically by common name
    if design in ("all", "1"):
        build_one_page(birds)
    if design in ("all", "2"):
        build_two_page(birds)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the Calvert Ct bird collages.")
    ap.add_argument("--design", choices=["all", "1", "2"], default="all",
                    help="which to build: 1 = single sheet, 2 = tape-up pair, "
                         "all = both (default)")
    main(ap.parse_args().design)
