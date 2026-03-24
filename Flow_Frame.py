# class Navbar(tk.Frame): ...
# class Toolbar(tk.Frame): ...
# class Statusbar(tk.Frame): ...
# class Main(tk.Frame): ...


import sys
if "Tkinter" not in sys.modules:
    import tkinter as tk
import numpy as np
import pickle
from PIL import ImageTk,Image
import cv2
import time
from Caper import Video,Rectangle,CrossCorrelation
import datetime
from Utilities import *
from FrameClasses import VideoFrame,ParticipantList,MatplotlibFrame,Menu,FlowFrame

# import matplotlib.pyplot as plt
# from matplotlib.figure import Figure
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# from matplotlib.backend_bases import key_press_handler
# import pandas as pd
# import matplotlib.animation as animation
# import random
# from PIL import Image,ImageDraw,ImageFont
# import matplotlib.colors as colors
# import io
import sys
from webcolors import rgb_to_hex
from tkinter import ttk as ttk
# from FrameClasses import VideoFrame



class Flow_Frame(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super(Flow_Frame,self).__init__()
        self.master = master
        # self.main_frame=self.master.master_canvas
        self.master.configure(bg=self.master.color_hex)

        self.master.screen_width = self.master.winfo_screenwidth()
        self.master.screen_height = self.master.winfo_screenheight()

        self.participant_list = ParticipantList(self.master,path=self.master.flows_directory_path)
        self.video_frame = FlowFrame(self.master,path=self.master.selected_item)
        # self.matplotlib_frame = MatplotlibFrame(self.master)

        # self.master.bind("<Escape>",self.end_fullscreen)
        # self.main_frame.bind("<Configure>",self._resize)

        self.delay = 1
        self.test = 0

        # self.master.selected_item=None
        #self.master.previously_selected_item = ''
        self._pack()
        self.update()

    def _resize(self,event=None):
        # self.main_frame.configure(width=self.master.width,
        #                             height=self.master.height)
        self.video_frame._resize()
        pass

        #move all resizing here

    def _unpack(self):
        self.participant_list._unpack()
        self.video_frame._unpack()
        # self.matplotlib_frame._unpack()
        # self.main_frame.pack_forget()

    def _pack(self):
        self.participant_list._pack()
        self.video_frame._pack()
        # self.matplotlib_frame._pack()
        # self.main_frame.pack()

    def _destroy(self):
        self.participant_list._destroy()
        self.video_frame._destroy()
        # self.matplotlib_frame._destroy()

    def end_fullscreen(self,event):
        sys.exit()

    def update(self):

        # if self.master.repack_analyze_frame_command == True:
        #     self._unpack()
        #     self._pack()
        #     self.master.repack_analyze_frame_command = False

        if self.master.selected_item != None:
            if self.master.selected_item!=self.master.previously_selected_item:
                self.video_frame.set_video(self.master.selected_item)
                self.master.previously_selected_item=self.master.selected_item
                self.video_frame.update(force=True)

        self.test+=1
        self.video_frame.update()
        # self.matplotlib_frame.update()



#for fast optical flow
#https://github.com/opencv/opencv/blob/master/modules/python/test/test_umat.py#L22