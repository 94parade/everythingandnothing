"""Flat-field correction for photographed book pages on poster board.

Estimates the slow lighting gradient from the visible board, divides it out,
and maps the board to one shared target colour so pages blend when stacked.
Small, sharp shadows under the cut-outs are untouched (the fitted surface is a
low-order polynomial, so it can't follow them).
"""
import sys
import numpy as np
import cv2

# Shared board colour for every page (BGR). Warm off-white, kept below pure
# white so the cut-out paper (about 8-10% brighter than the board) still reads
# as a separate, raised layer.
TARGET_BGR = np.array([226.0, 232.0, 236.0], dtype=np.float32)
DEG = 3          # polynomial degree of the lighting surface
SMALL = 256      # working width for the fit


def design(xs, ys, deg=DEG):
    cols = []
    for i in range(deg + 1):
        for j in range(deg + 1 - i):
            cols.append((xs ** i) * (ys ** j))
    return np.stack(cols, axis=-1)


def fit_surface(img):
    h, w = img.shape[:2]
    sh = int(round(h * SMALL / w))
    small = cv2.resize(img, (SMALL, sh), interpolation=cv2.INTER_AREA).astype(np.float32)
    small = cv2.GaussianBlur(small, (3, 3), 0)
    logs = np.log(small + 1.0)
    L = logs.mean(axis=2)

    yy, xx = np.mgrid[0:sh, 0:SMALL].astype(np.float32)
    xn, yn = xx / (SMALL - 1) * 2 - 1, yy / (sh - 1) * 2 - 1
    A = design(xn.ravel(), yn.ravel())

    # Start: background = darker-than-median-ish smooth pixels (cut-outs are brighter)
    grad = cv2.Laplacian(L, cv2.CV_32F, ksize=3)
    mask = (np.abs(grad) < 0.02) & (L < np.percentile(L, 70))
    for _ in range(5):
        m = mask.ravel()
        coef, *_ = np.linalg.lstsq(A[m], L.ravel()[m], rcond=None)
        fit = (A @ coef).reshape(sh, SMALL)
        res = L - fit
        mask = (np.abs(res) < 0.025) & (np.abs(grad) < 0.03)
        mask = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)

    # Per-channel surface on the final background mask
    m = mask.ravel()
    surf_small = np.empty_like(logs)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A[m], logs[..., c].ravel()[m], rcond=None)
        surf_small[..., c] = (A @ coef).reshape(sh, SMALL)
    surf = cv2.resize(np.exp(surf_small) - 1.0, (w, h), interpolation=cv2.INTER_CUBIC)
    return surf, mask.mean()


def soft_clip(x, knee=246.0, top=255.0):
    over = x > knee
    span = top - knee
    y = x.copy()
    y[over] = knee + span * np.tanh((x[over] - knee) / span)
    return y


def flatten(path_in, path_out):
    img = cv2.imread(path_in).astype(np.float32)
    surf, frac = fit_surface(img)
    out = img / np.maximum(surf, 1.0) * TARGET_BGR
    out = soft_clip(out)
    cv2.imwrite(path_out, np.clip(out, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 95])
    return frac


if __name__ == "__main__":
    for p_in, p_out in zip(sys.argv[1::2], sys.argv[2::2]):
        frac = flatten(p_in, p_out)
        print(f"{p_out}: board pixels used {frac:.0%}")
