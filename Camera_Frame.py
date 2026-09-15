# import cv2
#
# video = cv2.VideoCapture(0)
#
# # self.video.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
# # self.video.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
# (grabbed, frame) = video.read()
# print(frame)
# print(video.get(cv2.CAP_PROP_FRAME_WIDTH))
# print(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
# print(video.get(cv2.CAP_PROP_FPS))
#
# video.isOpened()
# video.release()
# video.open(0)


# class Navbar(tk.Frame): ...
# class Toolbar(tk.Frame): ...
# class Statusbar(tk.Frame): ...
# class Main(tk.Frame): ...


import sys
if "Tkinter" not in sys.modules:
    import tkinter as tk
import numpy as np
import pickle
from PIL import ImageTk,Image,ImageDraw,ImageFont
import cv2
import time
from Caper import Video,Rectangle,VideoCamera,VideoStabilization
import datetime
from Utilities import *
from FrameClasses import VideoFrame,CameraFrameSettings
import os
import pandas as pd
from tkinter import messagebox
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
from FrameClasses import ParticipantList


#
# import cv2




import sys
from webcolors import rgb_to_hex
from tkinter import ttk as ttk
# from FrameClasses import VideoFrame






from webcolors import rgb_to_hex

class Camera_Frame(tk.Frame):
    def __init__(self,master,*args,**kwargs):

        super(Camera_Frame,self).__init__()


        self.master = master

        self.screen_width = master.winfo_screenwidth()
        self.screen_height = master.winfo_screenheight()

        self.size_of_frame_relative_to_screen = 0.5
        self.size_of_canvas_relative_to_frame = 0.7
        self.size_of_video_relative_to_canvas = 0.9

        self.main_w = int(self.screen_width * self.size_of_frame_relative_to_screen)
        self.main_h = int(self.screen_height * self.size_of_frame_relative_to_screen)


        self.canvas_w = self.main_w  # could be different? #canvas and frame same size now
        self.canvas_h = self.main_h  # could be different? #canvas and frame same size now
        self.video_canvas_w = self.canvas_w * self.size_of_video_relative_to_canvas
        self.video_canvas_h = self.canvas_h * self.size_of_video_relative_to_canvas

        self.size = (self.canvas_w,self.canvas_h)

        self.canvas = tk.Canvas(self.master,width=self.canvas_w,height=self.canvas_h,bg=self.master.color_hex,
                                borderwidth=0,highlightthickness=0)
        self.video_canvas = tk.Canvas(self.canvas,width=self.video_canvas_w,height=self.video_canvas_h,
                                      bg=self.master.color_hex,borderwidth=0,highlightthickness=0)

        self.camera_frame_settings = CameraFrameSettings(self.master)
        # self.settings_canvas = tk.Canvas(self.canvas,width=200,height=self.canvas_h,
        #                               bg=self.master.color_hex,borderwidth=0,highlightthickness=0)

        # self.participant_list = ParticipantList(self.master,path=self.master.recorded_video_directory_path)

        self.state = False
        self.master.record=False

        self.registered_time_points = []

        self.create_time_point = tk.Button(self.canvas,width=13,text='Register time',bg=self.master.color_hex,
                                           borderwidth=0,highlightthickness=0,font=self.master.font,
                                           command=self.register_time_point)


        self.master.video = VideoCamera(self.master.recorded_video_directory_path)
        self.frame = self.master.video.get_frame()

        def key(event):

            self.current_key = event.state
            print("pressed",repr(event.char))

            if event.char == 'p' or event.char == ' ':
                self.master.video.pause = 1 - self.master.video.pause
            if event.char == 'f':
                self.toggle_fullscreen()

        def key_release(event):
            self.current_key = None

        self.master.bind("<Key>",key)
        self.master.bind("<KeyRelease>",key_release)

        self.delay = 0
        self.ticker = 0


        self.previous_frame = self.frame
        self.frame_Image = Image.fromarray(self.frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        self.image_id = self.video_canvas.create_image(
            int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
            int((self.canvas_h * self.size_of_video_relative_to_canvas) / 2),
            image=self.frame)



        self.canvas_ratio = 1200 / 800

        #self.canvas.bind("<Configure>",self._resize_video_canvas)
        self.master.bind("<Escape>",self.end_fullscreen)


#,command=self.callback_capture


    def _pack(self):

        # self.settings_canvas.pack(side='right')
        self.camera_frame_settings._pack()
        # self.participant_list._pack()
        self.create_time_point.pack(side='bottom',anchor=tk.NE)  # should do only once

        #self.canvas.pack(expand=tk.YES)
        self.canvas.pack(anchor=tk.N,expand=tk.YES)
        self.pack(side="left")

    def _unpack(self):
        # self.fps_label.pack_forget()
        # self.participant_list._unpack()
        self.camera_frame_settings._unpack()
        self.create_time_point.pack_forget()
        self.canvas.pack_forget()
        self.pack_forget()

    def _destroy(self):
        # self.participant_list._destroy()
        self.canvas.destroy()
        self.destroy()

    def canvas_size(self,width,height):  # input canvas size, not video canvas
        target_width = width * self.size_of_video_relative_to_canvas
        target_height = height * self.size_of_video_relative_to_canvas

        if target_width / target_height > self.master.video.aspect_ratio_:  # för bred, använd höjden för att skala
            video_frame_w = int(target_height / self.master.video.aspect_ratio_)
            video_frame_h = int(target_height)
        else:
            video_frame_h = int(target_width * self.master.video.aspect_ratio_)
            video_frame_w = int(target_width)
        return video_frame_w,video_frame_h

    def _resize_video_canvas(self,event=None):

        if event != None:
            self.canvas_w = event.width
            self.canvas_h = event.height

        self.plot_canvas_w = int(self.canvas_w * 0.1)
        self.plot_canvas_h = int(self.canvas_h * 0.1)
        self.video_frame_w,self.video_frame_h = self.canvas_size(self.canvas_w,self.canvas_h)

        self.video_canvas.configure(width=self.video_frame_w,
                                    height=self.video_frame_h)
        self.canvas.create_window(int((self.canvas_w) / 2),int((self.canvas_h) / 2),window=self.video_canvas)
        self.image_id = self.video_canvas.create_image(self.video_frame_w / 2,self.video_frame_h / 2,
                                                       image=self.frame)

    def toggle_fullscreen(self,event=None):
        self.state = not self.state  # Just toggling the boolean
        self.master.attributes("-fullscreen",self.state)
        # self.generate_progress_bar()
        return "break"

    def end_fullscreen(self,event=None):
        self.state = False
        self.master.attributes("-fullscreen",False)
        sys.exit()
        # self.generate_progress_bar()
        return "break"

    def register_time_point(self):
        #time points are stored in seconds from the start of the recording
        recording_start = self.camera_frame_settings.recording_timestamp
        if recording_start is None:
            messagebox.showerror("Error","Start a recording before registering time points")
            return
        self.registered_time_points.append(
            (datetime.datetime.now() - recording_start).total_seconds())

        #updates the saved file if there is one.
        file_name = self.master.video.path[:-4] #removes .avi
        pd.DataFrame(self.registered_time_points).to_csv(
            os.path.join(self.master.statistics_directory_path, file_name+ '_registered_time_points.csv'))

    def update(self,force=False):

        self.ticker+=1

        if self.ticker%12==0:
            self.camera_frame_settings.update_textbutton()
            self.camera_frame_settings.update_recording_length_textbutton()

        frame = self.master.video.get_frame()
        self.previous_frame = frame

        if self.master.record is True:
            self.master.video.save_frame(frame)

        self.frame_Image = Image.fromarray(frame)

        try:  # error only happens on program start
            self.frame_Image = self.frame_Image.resize((self.video_frame_w,
                                                        self.video_frame_h),
                                                       Image.Resampling.LANCZOS)
        except:
            self.video_frame_w,self.video_frame_h = self.canvas_size(self.canvas_w,self.canvas_h)


        #move this to some button or something
        # draw = ImageDraw.Draw(self.frame_Image)
        # draw.text((7,0),  'FPS: '+str(int(self.fps)), fill = (255,255,255),font=ImageFont.truetype(os.path.join('Source','Quicksand-Regular.ttf'),size=int(self.video_frame_h/33)))


        self.frame = ImageTk.PhotoImage(self.frame_Image)

        self.video_canvas.itemconfig(self.image_id,image=self.frame)
