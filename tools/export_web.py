"""Export corrected pages as web-ready WebP (several widths) + JPEG fallback.

Writes into <site>/pages/ and prints a JSON manifest of sizes for index.html.
"""
import sys, os, json
from PIL import Image

SRC, SITE = sys.argv[1], sys.argv[2]

ORDER = [
    ("p01", "page-01_IMG_1570"), ("p02", "page-02_IMG_1575-1"), ("p03", "page-03_IMG_1609"),
    ("p04", "page-04_IMG_1578"), ("p05", "page-05_IMG_1579"), ("p06", "page-06_IMG_1586"),
    ("p07", "page-07_IMG_1592"), ("p08", "page-08_IMG_1593"), ("p09", "page-09_IMG_1594"),
    ("p10", "page-10_IMG_1599"), ("p11", "page-11_IMG_1661"), ("p12", "page-12_IMG_1602"),
    ("p13", "page-13_IMG_1604"), ("p14", "page-14_IMG_1663"), ("p15", "page-15_IMG_1608"),
    ("p16", "page-16_IMG_1612"), ("p17", "page-17_IMG_1613"), ("p18", "page-18_IMG_1619-1"),
    ("p19", "page-19_IMG_1620"), ("p20", "page-20_IMG_1627"), ("p21", "page-21_IMG_1626"),
    ("p22", "page-22_IMG_1664"), ("p23", "page-23_IMG_1623"), ("p24", "page-24_IMG_1651"),
    ("p25", "page-25_IMG_1633"), ("p26", "page-26_IMG_1666"), ("p27", "page-27_IMG_1646"),
    ("p28", "page-28_IMG_1645"), ("p29", "page-29_IMG_1647"), ("p30", "page-30_IMG_1609"),
    ("p31", "page-31_IMG_1634"), ("p32", "page-32_IMG_1636"), ("p33", "page-33_IMG_1568"),
    ("p34", "page-34_IMG_1673"), ("copyright", "cover-01_IMG_1574"),
]
WIDTHS = [640, 1000, 1500]

out_dir = os.path.join(SITE, "pages")
os.makedirs(out_dir, exist_ok=True)
manifest = {}
for key, name in ORDER:
    im = Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")
    w, h = im.size
    widths = [x for x in WIDTHS if x < w] + [w]
    for tw in widths:
        th = round(h * tw / w)
        r = im if tw == w else im.resize((tw, th), Image.LANCZOS)
        r.save(os.path.join(out_dir, f"{key}-{tw}.webp"), "WEBP", quality=84, method=6)
    fb_w = min(1500, w)
    fb = im if fb_w == w else im.resize((fb_w, round(h * fb_w / w)), Image.LANCZOS)
    fb.save(os.path.join(out_dir, f"{key}.jpg"), "JPEG", quality=84, optimize=True, progressive=True)
    manifest[key] = {"w": w, "h": h, "widths": widths}

# Social share image from the title page
t = Image.open(os.path.join(SRC, "page-01_IMG_1570.jpg")).convert("RGB")
t = t.resize((1200, round(t.height * 1200 / t.width)), Image.LANCZOS)
top = max(0, (t.height - 630) // 2)
t.crop((0, top, 1200, top + 630)).save(os.path.join(SITE, "og.jpg"), "JPEG", quality=86)

print(json.dumps(manifest))
