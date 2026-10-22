"""Puts every page on a consistent 4:3 canvas of levelled board.

Pages that were cropped to odd shapes, or whose cut-outs sit tight against an
edge, get extra board added around them. The added board is synthetic: the
shared board colour plus grain matched to the photo, blended into the photo
over a soft seam so the join doesn't show. The photo itself is never scaled,
so every page keeps the same camera scale.

Usage: python3 tools/pad.py <levelled dir> <out dir>
"""
import sys, os, glob
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refine import paper_mask  # noqa: E402

TARGET_BGR = np.array([226.0, 232.0, 236.0], dtype=np.float32)
BASE = (2016, 1512)   # the uncropped photo size
SEAM = 90             # px over which the photo blends into added board

# Per-page canvas and placement. Anything not listed is centred on BASE.
#   size: canvas (w, h); at: (left, top) offset of the photo on the canvas
OVERRIDES = {
    # tight to the left edge / short crop: more room on the left and top
    "page-31": {"size": (2140, 1605), "at": (110, 250)},
    # short crop with cut-outs near the top: most of the added height above
    "page-27": {"size": BASE, "at": (48, 250)},
    "page-26": {"size": BASE, "at": (40, 150)},
    # content within ~3-4% of an edge: a slightly larger canvas all round
    "page-13": {"size": (2120, 1590)},
    "page-24": {"size": (2120, 1590)},
    "page-25": {"size": (2120, 1590)},
}


def grain_std(img):
    """Fine grain of the bare board in this photo (per channel)."""
    hp = img - cv2.GaussianBlur(img, (0, 0), 3)
    L = img.mean(2)
    board = np.abs(L / TARGET_BGR.mean() - 1) < 0.02
    board &= np.abs(cv2.Laplacian(cv2.GaussianBlur(L, (3, 3), 0), cv2.CV_32F)) < 2
    return hp[board].std(axis=0) if board.sum() > 1000 else np.array([1.2, 1.2, 1.2], np.float32)


def synthetic_board(w, h, std, seed):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, (h, w, 3)).astype(np.float32)
    noise = cv2.GaussianBlur(noise, (0, 0), 0.8)
    noise /= noise.reshape(-1, 3).std(axis=0) + 1e-6
    return TARGET_BGR + noise * std


def pad_page(img, key, seed):
    h, w = img.shape[:2]
    o = OVERRIDES.get(key, {})
    cw, ch = o.get("size", BASE)
    cw, ch = max(cw, w), max(ch, h)
    # Already the standard size give or take a couple of pixels: leave it alone
    if key not in OVERRIDES and cw - w <= 2 and ch - h <= 2:
        return img
    x, y = o.get("at", ((cw - w) // 2, (ch - h) // 2))
    x, y = min(max(x, 0), cw - w), min(max(y, 0), ch - h)
    if (cw, ch) == (w, h):
        return img

    canvas = synthetic_board(cw, ch, grain_std(img), seed)
    # Alpha: 1 inside the photo, easing to 0 across SEAM px at any edge that meets added board
    a = np.ones((h, w), np.float32)
    ramp = (1 - np.cos(np.linspace(0, np.pi, SEAM))) / 2
    if x > 0:          a[:, :SEAM] *= ramp[None, :]
    if x + w < cw:     a[:, -SEAM:] *= ramp[::-1][None, :]
    if y > 0:          a[:SEAM, :] *= ramp[:, None]
    if y + h < ch:     a[-SEAM:, :] *= ramp[::-1][:, None]
    # Never fade cut-out paper (or the shadow just around it) into the added board
    keep = cv2.dilate(paper_mask(img), np.ones((31, 31), np.uint8)).astype(np.float32)
    keep = cv2.GaussianBlur(keep, (0, 0), 5)
    a = np.maximum(a, keep)
    region = canvas[y:y + h, x:x + w]
    canvas[y:y + h, x:x + w] = img * a[..., None] + region * (1 - a[..., None])
    return canvas


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for i, f in enumerate(sorted(glob.glob(os.path.join(src, "*.jpg")))):
        name = os.path.basename(f)
        img = cv2.imread(f).astype(np.float32)
        # Only book pages get the shared canvas; the small copyright card keeps its own size
        out = pad_page(img, name[:7], seed=i) if name.startswith("page-") else img
        cv2.imwrite(os.path.join(dst, name), np.clip(out, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{name}: {img.shape[1]}x{img.shape[0]} -> {out.shape[1]}x{out.shape[0]}")
