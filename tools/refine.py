"""Second pass: finer board levelling so page edges meet the target colour.

Builds a smooth map of the board only (cut-outs, ink and shadows masked out),
then rescales so the board equals TARGET everywhere. Because masked pixels
don't contribute to the map, the soft shadows under cut-outs are preserved.

Where cut-outs cover most of an area there is little bare board nearby, so the
map is filled in from progressively wider neighbourhoods (multi-scale) instead
of being left uncorrected.
"""
import sys, os, glob
import numpy as np
import cv2

TARGET_BGR = np.array([226.0, 232.0, 236.0], dtype=np.float32)
SMALL = 320
SCALES = (SMALL / 14.0, SMALL / 6.0, SMALL / 2.5)  # blur sigmas, fine to coarse


EDGE_RES = 900  # working width for finding the scissor-cut edges


def paper_mask(img):
    """Cut-out paper (and everything drawn on it), found as the regions enclosed
    by crisp cut edges. Board is whatever connects to the photo's border
    without crossing one. Returned at full resolution, 1 = paper."""
    h, w = img.shape[:2]
    eh = int(round(h * EDGE_RES / w))
    L = cv2.resize(img, (EDGE_RES, eh), interpolation=cv2.INTER_AREA).mean(2)
    L8 = np.clip(L, 0, 255).astype(np.uint8)
    edges = cv2.Canny(cv2.GaussianBlur(L8, (3, 3), 0), 6, 16)
    walls = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=3) > 0
    free = (~walls).astype(np.uint8)
    n, lab = cv2.connectedComponents(free, connectivity=4)
    border_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    board = np.isin(lab, list(border_labels))
    # Walls hugging board on both sides are board texture, not paper: grow board back over them
    board = cv2.dilate(board.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    paper = ~board
    # Small specks (dust, noise) aren't cut-outs
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(paper.astype(np.uint8))
    keep = np.zeros(n2, bool)
    keep[1:] = st2[1:, cv2.CC_STAT_AREA] > 60
    paper = keep[lab2]
    return cv2.resize(paper.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)


def board_mask(small, paper_small):
    L = small.mean(2)
    # Judge "board" against this photo's own typical board brightness, so the
    # same test works on raw photos (darker, uneven) and already-levelled ones.
    outside = paper_small == 0
    tL = float(np.median(L[outside])) if outside.sum() > 100 else float(np.median(L))
    grad = np.abs(cv2.Laplacian(cv2.GaussianBlur(L, (3, 3), 0), cv2.CV_32F, ksize=3))
    # Board: outside every cut-out, not too far from the board colour (allows for
    # brighter-lit strips and corners), and smooth.
    mask = (paper_small == 0) & (np.abs(L / tL - 1) < 0.15) & (grad < 4)
    # Stay clear of the soft shadows right around each cut-out
    near_paper = cv2.dilate(paper_small, np.ones((13, 13), np.uint8)) > 0
    mask &= ~near_paper
    return cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)


def board_map(img, paper=None):
    h, w = img.shape[:2]
    sh = int(round(h * SMALL / w))
    small = cv2.resize(img, (SMALL, sh), interpolation=cv2.INTER_AREA)
    if paper is None:
        paper = paper_mask(img)
    paper_small = (cv2.resize(paper.astype(np.float32), (SMALL, sh), interpolation=cv2.INTER_AREA) > 0.01).astype(np.uint8)
    mask = board_mask(small, paper_small)

    def estimate(mask):
        # Coarsest fallback: this page's overall board colour.
        m = mask > 0
        bm = np.broadcast_to(np.median(small[m], axis=0) if m.sum() > 50 else TARGET_BGR, small.shape).copy()
        # Blend in finer scales wherever they have enough bare board to trust.
        for sigma in reversed(SCALES):
            num = np.stack([cv2.GaussianBlur(small[..., c] * mask, (0, 0), sigma, borderType=cv2.BORDER_REFLECT)
                            for c in range(3)], -1)
            den = cv2.GaussianBlur(mask, (0, 0), sigma, borderType=cv2.BORDER_REFLECT)[..., None]
            est = num / np.maximum(den, 1e-4)
            wgt = np.clip(den / 0.25, 0, 1)
            bm = est * wgt + bm * (1 - wgt)
        return bm

    bm = estimate(mask)
    # Drop anything distinctly brighter or darker than the board around it
    # (paper the edge test missed, stray marks), then estimate again.
    for _ in range(2):
        ratio = small.mean(2) / np.maximum(bm.mean(2), 1)
        outlier = (np.abs(ratio - 1) > 0.03).astype(np.uint8)
        outlier = cv2.dilate(outlier, np.ones((5, 5), np.uint8)) > 0
        mask = mask * (~outlier)
        bm = estimate(mask)
    return cv2.resize(bm, (w, h), interpolation=cv2.INTER_CUBIC)


def soft_clip(x, knee=246.0, top=255.0):
    span = top - knee
    return np.where(x > knee, knee + span * np.tanh((x - knee) / span), x)


def refine(p_in, p_out):
    img = cv2.imread(p_in).astype(np.float32)
    bm = board_map(img)
    out = soft_clip(img / np.maximum(bm, 1) * TARGET_BGR)
    cv2.imwrite(p_out, np.clip(out, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92])


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, "*.jpg"))):
        refine(f, os.path.join(dst, os.path.basename(f)))
        print("done", os.path.basename(f))
