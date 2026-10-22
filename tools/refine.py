"""Second pass: finer board levelling so page edges meet the target colour.

Builds a smooth map of the board only (cut-outs, ink and shadows masked out),
then rescales so the board equals TARGET everywhere. Because masked pixels
don't contribute to the map, the soft shadows under cut-outs are preserved.
"""
import sys, os, glob
import numpy as np
import cv2

TARGET_BGR = np.array([226.0, 232.0, 236.0], dtype=np.float32)
SMALL = 320


def board_map(img):
    h, w = img.shape[:2]
    sh = int(round(h * SMALL / w))
    small = cv2.resize(img, (SMALL, sh), interpolation=cv2.INTER_AREA)
    L = small.mean(2)
    tL = TARGET_BGR.mean()
    grad = np.abs(cv2.Laplacian(cv2.GaussianBlur(L, (3, 3), 0), cv2.CV_32F, ksize=3))
    # Board = near target brightness, smooth. Cut-outs are brighter, shadows/ink darker.
    mask = (np.abs(L / tL - 1) < 0.035) & (grad < 4)
    mask = cv2.erode(mask.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32)
    sigma = SMALL / 14.0
    num = np.stack([cv2.GaussianBlur(small[..., c] * mask, (0, 0), sigma, borderType=cv2.BORDER_REFLECT) for c in range(3)], -1)
    den = cv2.GaussianBlur(mask, (0, 0), sigma, borderType=cv2.BORDER_REFLECT)[..., None]
    bm = np.where(den > 1e-3, num / np.maximum(den, 1e-3), TARGET_BGR)
    # Where there's barely any board nearby (big cut-outs), fall back to target.
    wgt = np.clip(den / 0.25, 0, 1)
    bm = bm * wgt + TARGET_BGR * (1 - wgt)
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
