import cv2
import numpy as np
from Utilities import *
import tkinter as tk
from PIL import ImageTk,Image
import datetime
import glob
import skvideo.io as io
import SingleStepDFT as DFT
import pandas as pd

from Caper import Video

a=None
a = Video('Data/FP07_Qföre_18-Oct-2019_09-13-46.avi')
n = 20
a.load(n)
a.number_of_reference_frames=3
a.stabilize_video()

