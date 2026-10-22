# Everything & Nothing

A picture book by Phil Osgood, written and illustrated by hand, photographed
page by page, and presented as one continuous scroll.

Live site: https://www.everythingandnothing.space

## How it's put together

- `index.html` — the whole site. One page, no framework, no build step.
- `pages/` — every book page in several widths (WebP) plus a JPEG fallback.
- `og.jpg` — the preview image shown when the link is shared.
- `tools/` — the scripts that made the images (not deployed):
  - `flatten.py` — first lighting pass: removes the overall light falloff across each photo.
  - `refine.py` — second pass: levels the board to one shared colour so pages blend edge to edge, while keeping the shadows under the cut-outs.
  - `export_web.py` — writes the web sizes into `pages/`.
  - `build_index.py` — writes `index.html` from the page list and alt text.

## Changing a page

1. Run the new photo through `flatten.py` then `refine.py`.
2. Run `export_web.py` to regenerate `pages/`.
3. Edit the page list or alt text in `tools/build_index.py` if needed, then run it.
4. Commit and push; Vercel deploys automatically.
