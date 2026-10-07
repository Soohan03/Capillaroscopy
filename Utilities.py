"""Small helpers for the video classes in Caper.py."""
import cv2
from scipy import signal

# The sharpness score moved into the measurement engine; re-exported for Caper.py.
from capillary.quality import calculate_blur  # noqa: F401


def clahe(img,clip_limit = 7.65,tileGridSize=(3,3)): #255
    clahe_filter = cv2.createCLAHE(clipLimit=clip_limit,tileGridSize=tileGridSize)
    return clahe_filter.apply((img).astype('uint8'))

def median_filter(img,kernel=[7,7]):
    return signal.medfilt(img,kernel)
