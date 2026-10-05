import cv2
import numpy as np
from image_registration.fft_tools import correlate2d, fast_ffts
from scipy import signal as signal
import math
import pandas as pd

import pickle

def pickle_save(file,filename):
    with open(filename, 'wb') as handle:
        pickle.dump(file, handle, protocol=pickle.HIGHEST_PROTOCOL)

def pickle_load(filename):
    with open(filename, 'rb') as handle:
        return pickle.load(handle)

def calculate_blur(img): #255 img

    rows,cols = img.shape
    crow,ccol = int(rows / 2),int(cols / 2)
    f = np.fft.fft2(img / 255.0)
    fshift = np.fft.ifftshift(f)
    fshift[crow - 75:crow + 75,ccol - 75:ccol + 75] = 0
    f_ishift = np.fft.ifftshift(fshift)
    img_fft = np.fft.ifft2(f_ishift)
    return np.mean(np.abs(img_fft))  # calibrate this by running all the videos and checking average, then set arbitrary threshold...

def clahe(img,clip_limit = 7.65,tileGridSize=(3,3),nthreads=1,use_numpy_fft=True): #255

    # fft2,ifft2 = fftn,ifftn = fast_ffts.get_ffts(nthreads=nthreads,use_numpy_fft=use_numpy_fft)
    clahe_filter = cv2.createCLAHE(clipLimit=clip_limit,tileGridSize=tileGridSize)
    return clahe_filter.apply((img).astype('uint8'))

def median_filter(img,kernel=[7,7]):
    return signal.medfilt(img,kernel)


def seconds_to_hms_string(seconds):
    m,s = divmod(seconds,60)
    h,m = divmod(m,60)
    return '{:d}:{:02d}:{:02d}'.format(h,m,s)

def rgb_to_negR_posG(im,max_val=255.0):
    im = np.array(im).astype(float)
    return (((-0.5*im[:,:,0])+(1.5*im[:,:,1])+(max_val*0.5))/2.0).astype(np.uint8)


def distance_between_two_points(y1,y2,x1,x2):
    dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return dist
