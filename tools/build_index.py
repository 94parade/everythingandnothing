"""Builds index.html from the page list below and the image sizes in pages/.

Run from the repo root:  python3 tools/build_index.py
"""
import html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES_DIR = os.path.join(ROOT, "pages")

TITLE = "Everything & Nothing"
AUTHOR = "Phil Osgood"
BOARD = "#ECE8E2"  # matches the levelled poster-board colour in every page image

# (image key, alt text). Alt text transcribes the words on each page so screen
# readers and search engines can read the book.
PAGES = [
    ("p01", "Everything & Nothing"),
    ("p02", "By Phil Osgood"),
    ("p03", "A looping line of curls."),
    ("p04", "Often upon a time..."),
    ("p05", "there were 2 twin siblings..."),
    ("p06", "Everything! Beside the word stands Everything, a character drawn as a colorful swirling tornado."),
    ("p07", "And Nothing. Beside the word stands Nothing, a character drawn as a tangled black scribble."),
    ("p08", "They didn't look alike"),
    ("p09", "They didn't have much in common either..."),
    ("p10", "Everything was always trying to do stuff!"),
    ("p11", "Everything says: “First I have to get dressed and then I need to get some food and then I need to go into town...”"),
    ("p12", "And Nothing would be like... Nothing says: “Yeah I don't want to do any of that.”"),
    ("p13", "Everything would say... Everything says: “But we have to do our homework and do our chores and then play outside and then take a bath...”"),
    ("p14", "But Nothing would just reply... Nothing says: “Nope, sorry. Not into it right now.”"),
    ("p15", "The twins could never agree! Nothing and Everything stand side by side."),
    ("p16", "Sometimes they wondered how they could even be related!"),
    ("p17", "Their mother, Someone, heard them arguing one day and asked them what was wrong... Someone is drawn as a triangle."),
    ("p18", "Everything says: “He never wants to do anything!” Nothing says: “Why can't we just relax?”"),
    ("p19", "Between Nothing and Everything, one speech bubble: “How can twins be so terribly different!?”"),
    ("p20", "Their mother told them a story about how she met their father..."),
    ("p21", "...who was Somewhere. Somewhere is drawn as a rectangle."),
    ("p22", "Someone tells the twins: “We met in school. He was always forgetting to bring a pencil to class. I always had an extra. He asked me to borrow a pencil so many times!”"),
    ("p23", "A classroom with the alphabet on the wall. Somewhere asks for a pencil, and Someone is nearby."),
    ("p24", "Someone, holding a pencil next to Somewhere, says: “You see? Your father is very forgetful, but I am always prepared.”"),
    ("p25", "Someone and Somewhere tell the twins: “We seem to be opposites, but actually we are a perfect team.”"),
    ("p26", "The twins understood and decided to compromise."),
    ("p27", "They could do a few of the tasks that Everything wanted to do..."),
    ("p28", "...and still make time for Nothing as well!"),
    ("p29", "Everything and Nothing share one speech bubble: “That's something!”"),
    ("p30", "A looping line of curls."),
    ("p31", "Because Somewhere's always better when Someone is around..."),
    ("p32", "And Nothing isn't Nothing without Everything abound..."),
    ("p33", "THE END"),
    ("p34", "Dedicated to my darling wife, the Someone to my Somewhere. For Everything she does, and also when she does Nothing..."),
    ("copyright", "Copyright 2017 By Phil Osgood"),
]


def sizes_for(key):
    widths = []
    for f in os.listdir(PAGES_DIR):
        m = re.fullmatch(re.escape(key) + r"-(\d+)\.webp", f)
        if m:
            widths.append(int(m.group(1)))
    widths.sort()
    full = widths[-1]
    # height from the JPEG fallback (same aspect as all variants)
    from struct import unpack
    with open(os.path.join(PAGES_DIR, f"{key}.jpg"), "rb") as fh:
        data = fh.read()
    i = 2
    while i < len(data):
        marker, length = data[i + 1], unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = unpack(">HH", data[i + 5:i + 9])
            break
        i += 2 + length
    return widths, w, h


def figure(index, key, alt):
    widths, w, h = sizes_for(key)
    srcset = ", ".join(f"pages/{key}-{x}.webp {x}w" for x in widths)
    eager = index < 2
    loading = 'fetchpriority="high"' if eager else 'loading="lazy"'
    cls = "page small" if key == "copyright" else "page"
    sizes = "(max-width: 640px) 60vw, 480px" if key == "copyright" else "(max-width: 1240px) 100vw, 1240px"
    return (
        f'    <picture class="{cls}">\n'
        f'      <source type="image/webp" srcset="{srcset}" sizes="{sizes}">\n'
        f'      <img src="pages/{key}.jpg" width="{w}" height="{h}" alt="{html.escape(alt)}" decoding="async" {loading}>\n'
        f'    </picture>'
    )


def build():
    figures = "\n".join(figure(i, k, a) for i, (k, a) in enumerate(PAGES))
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(TITLE)}</title>
  <meta name="author" content="{AUTHOR}">
  <meta name="description" content="{html.escape(TITLE)}, a picture book by {AUTHOR}.">
  <meta name="theme-color" content="{BOARD}">
  <meta name="color-scheme" content="light">
  <link rel="canonical" href="https://www.everythingandnothing.space/">
  <meta property="og:type" content="book">
  <meta property="og:title" content="{html.escape(TITLE)}">
  <meta property="og:description" content="A picture book by {AUTHOR}.">
  <meta property="og:url" content="https://www.everythingandnothing.space/">
  <meta property="og:image" content="https://www.everythingandnothing.space/og.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preload" as="image" type="image/webp"
        imagesrcset="pages/p01-640.webp 640w, pages/p01-1000.webp 1000w, pages/p01-1500.webp 1500w, pages/p01-2016.webp 2016w"
        imagesizes="(max-width: 1240px) 100vw, 1240px">
  <style>
    :root {{ --board: {BOARD}; }}
    html, body {{ margin: 0; padding: 0; background: var(--board); }}
    body {{ min-height: 100vh; -webkit-text-size-adjust: 100%; }}
    .book {{
      /* Each page fits within the screen height on desktop, full width on phones */
      width: min(100%, 1240px, 130vh);
      margin: 0 auto;
    }}
    .page {{ display: block; }}
    .page img {{
      display: block;
      width: 100%;
      height: auto;
      background: var(--board);
      /* Feather the photo's outer edge into the board colour so no page rectangle shows */
      -webkit-mask-image:
        linear-gradient(to right, transparent 0, #000 1.5%, #000 98.5%, transparent 100%),
        linear-gradient(to bottom, transparent 0, #000 1.5%, #000 98.5%, transparent 100%);
      -webkit-mask-composite: source-in;
      mask-image:
        linear-gradient(to right, transparent 0, #000 1.5%, #000 98.5%, transparent 100%),
        linear-gradient(to bottom, transparent 0, #000 1.5%, #000 98.5%, transparent 100%);
      mask-composite: intersect;
    }}
    .page.small {{ width: min(60%, 480px); margin: 4vh auto 8vh; }}
    .visually-hidden {{
      position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0;
      overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
    }}
  </style>
</head>
<body>
  <main class="book">
    <h1 class="visually-hidden">{html.escape(TITLE)} by {AUTHOR}</h1>
{figures}
  </main>
</body>
</html>
"""
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    print("wrote index.html with", len(PAGES), "images")


if __name__ == "__main__":
    build()
