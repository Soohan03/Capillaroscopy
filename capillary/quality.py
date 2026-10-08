"""Per-frame image quality.

`calculate_blur` is the sharpness score saved with every velocity data set
(``___blur_vector.csv``) and used by the stabilizer (`capillary.stabilize`) to
pick its reference frames. It lived in `Utilities.py` until the 2026-10 GUI
rebuild and moved here unchanged; `Utilities.py` itself was removed on
2026-10-08.
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
