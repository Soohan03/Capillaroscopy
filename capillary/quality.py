"""Per-frame image quality.

`calculate_blur` is the sharpness score the stabilizer (`capillary.stabilize`)
uses to pick its reference frames.
"""

from __future__ import annotations

import numpy as np


def calculate_blur(img):
    """High-frequency energy of an 8-bit greyscale frame: larger is sharper.

    The centre 150x150 block of the shifted spectrum (the low frequencies) is
    zeroed and the mean magnitude of what remains is returned. The value is
    only meaningful relative to other frames of similar content.
    """
    rows, cols = img.shape
    crow, ccol = int(rows / 2), int(cols / 2)
    f = np.fft.fft2(img / 255.0)
    fshift = np.fft.ifftshift(f)
    fshift[crow - 75:crow + 75, ccol - 75:ccol + 75] = 0
    f_ishift = np.fft.ifftshift(fshift)
    img_fft = np.fft.ifft2(f_ishift)
    return np.mean(np.abs(img_fft))
