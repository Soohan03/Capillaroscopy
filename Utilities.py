"""Small helpers shared by the GUI and the video classes in Caper.py."""
import pickle

import cv2
import numpy as np
from scipy import signal

# The sharpness score moved into the measurement engine; re-exported for Caper.py.
from capillary.quality import calculate_blur  # noqa: F401


def pickle_save(file,filename):
    with open(filename, 'wb') as handle:
        pickle.dump(file, handle, protocol=pickle.HIGHEST_PROTOCOL)

def pickle_load(filename):
    with open(filename, 'rb') as handle:
        return pickle.load(handle)

def clahe(img,clip_limit = 7.65,tileGridSize=(3,3)): #255
    clahe_filter = cv2.createCLAHE(clipLimit=clip_limit,tileGridSize=tileGridSize)
    return clahe_filter.apply((img).astype('uint8'))

def median_filter(img,kernel=[7,7]):
    return signal.medfilt(img,kernel)

def rgb_to_negR_posG(im,max_val=255.0):
    im = np.array(im).astype(float)
    return (((-0.5*im[:,:,0])+(1.5*im[:,:,1])+(max_val*0.5))/2.0).astype(np.uint8)
