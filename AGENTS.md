# AGENTS.md — working on calvert-ct-birds

This repo builds a labeled field-guide collage of the birds seen on Calvert Ct.
This file is the playbook for an agent (you) maintaining it. Read it fully before
adding birds or changing the build.

## What's here

```
birds.txt                       The observed list, in display order: "Common Name | scientific-stem"
build_collage.py                Builds the collages from birds.txt + illustrations/
library-index.csv               Lookup: scientific-stem -> common name, family, CA status (all 249 available species)
illustrations/                  The full source library, 450 PNGs (~249 species, most with a -2 "flying" pose)
birds-of-calvert-ct.png         Design 1: every bird on one US Letter landscape sheet
birds-of-calvert-ct-page1.png   Design 2, top sheet: title + first half, scaled larger
birds-of-calvert-ct-page2.png   Design 2, bottom sheet: second half, no title
birds-of-calvert-ct-2page.png   Page 1 stacked over page 2 — a preview of the taped-up poster
```

All generated sheets are US Letter landscape (8.5x11) at 300 dpi (3300x2550 px),
so they scale to fill the page when printed. Design 2 is two sheets you print
and tape together top-to-bottom; with half the birds each they're larger and
more legible. `python3 build_collage.py` rebuilds all four in one pass. The PNGs
are committed so the latest is always visible.

`illustrations/` is the master art library copied from `~/Work/AvianVisitors/avian/assets/illustrations`.
It holds far more species than we've observed — that's deliberate, so any newly
spotted bird can be added without hunting for art. The *observed* subset is
whatever is listed in `birds.txt`; nothing else from the library appears in the
collage.

Filenames are the scientific binomial, lowercased and hyphenated: `Icterus
bullockii` → `icterus-bullockii.png`. The standing pose is `<stem>.png`; the
flying pose, when it exists, is `<stem>-2.png`. The collage uses the standing
pose (falling back to flying if standing is missing).

## Adding a bird — the normal request

Ben will say something like *"I just saw an Oriole! Add it!"* — usually a common
name, sometimes vague. Do this:

1. **Resolve the common name to a stem.** Search `library-index.csv` for the
   name:
   ```bash
   grep -i oriole library-index.csv
   ```
   - **One match** → use that stem.
   - **Several matches** (e.g. "Oriole" → Bullock's, Hooded, Baltimore, Scott's)
     → this is California, so prefer the species whose `ca_status` makes it
     plausible, but **don't guess silently**. List the candidates and ask Ben
     which one. Bullock's is the expected backyard oriole in most of CA; Baltimore
     is a rare vagrant. Use the `ca_status` column to steer the question.
   - **No match in the index** → the species may still be in the library under a
     different name, so also try the scientific name if you know it:
     `ls illustrations/ | grep <genus>`. If the art genuinely isn't there, tell
     Ben we don't have an illustration for it — we can't add it.

2. **Confirm the art exists:** `ls illustrations/<stem>.png`. If only the flying
   pose exists (`<stem>-2.png`), that's fine — the build falls back to it.

3. **Add one line to `birds.txt`:** `Common Name | scientific-stem`. Use the
   exact common name from `library-index.csv`. Append it at the end unless Ben
   wants a particular order (the collage reads top-to-bottom, left-to-right, 6
   per row).

4. **Rebuild and look at it:**
   ```bash
   python3 build_collage.py
   ```
   Open `birds-of-calvert-ct.png` and check the new bird: right species, sane
   size, label not overrunning. If it shows a faint rectangular halo or dotted
   background (a rough cutout in the source art), add its stem to the `NOISY`
   set near the top of `build_collage.py` and rebuild — that triggers the
   threshold + morphological-open cleanup that fixes the turkey.

5. **Commit and push:**
   ```bash
   git add birds.txt birds-of-calvert-ct.png && git commit -m "Add <Common Name>" && git push
   ```

Adding several birds at once is the same loop — edit all the `birds.txt` lines,
build once, commit once. A few birds is a quick grep-and-edit; don't reach for a
multi-agent workflow for it.

## Rebuilding `library-index.csv`

You won't usually need to. It was generated once by mapping every filename stem
to its common name with a fan-out + adversarial-verify workflow. If new art is
added to `illustrations/`, regenerate the index so the new species are
searchable. The workflow that built it lives in the session history; the short
version: batch the stems, have one agent per batch return
`stem, scientific, common, family, ca_status`, have a second independent agent
re-derive and correct each batch, then write the merged CSV sorted by stem.

## Design notes (don't regress these)

- **Area normalization.** Each bird is scaled so its content occupies roughly
  equal pixel *area*, not fit into a fixed square. Without this, wide perched
  birds shrink to a band and tall birds balloon. This is the single biggest
  reason the collage looks even. See `TARGET_AREA` in `build_collage.py`.
- **Two-line labels.** Labels use `caption:` so long names (e.g. "Chestnut-backed
  Chickadee") wrap to two lines, which lets every label sit at the same large
  point size instead of auto-shrinking the long ones.
- **The look:** warm paper `#FAF7F0`, Baskerville labels, title "Birds of Calvert
  Ct". This is the style Ben picked (originally "collage-A-fieldguide"). Earlier
  dark and mosaic variants were dropped on purpose — don't reintroduce them
  unless asked.

## Known filename quirks

- `leiothlypis-lucidae` is a misspelling of *Leiothlypis luciae* — **Lucy's
  Warbler**. The index records the correction in its `note` column; the stem
  (filename) stays as-is.
- Genera in the library follow current AOS taxonomy: `Dryobates` (not Picoides)
  for most small woodpeckers, `Leiothlypis` for the former Vermivora warblers,
  `Urile penicillatus` for Brandt's Cormorant, `Aphelocoma woodhouseii` for
  Woodhouse's Scrub-Jay. `picoides-arcticus` (Black-backed Woodpecker) correctly
  stays in Picoides.

## Requirements

- ImageMagick 7 (`magick`). Fonts used: Baskerville (macOS system font).
