import datetime
import os
import sys
import tkinter as tk
from tkinter import messagebox

import pandas as pd
from PIL import Image,ImageTk

from Caper import VideoCamera
from FrameClasses import CameraFrameSettings
from Utilities import video_stem


class Camera_Frame(tk.Frame):
    """Capture tab: live camera view, recording, and registering time points during a recording."""
    def __init__(self,master,*args,**kwargs):

        super(Camera_Frame,self).__init__()

        self.master = master

        self.screen_width = master.winfo_screenwidth()
        self.screen_height = master.winfo_screenheight()

        self.size_of_frame_relative_to_screen = 0.5
        self.size_of_video_relative_to_canvas = 0.9

        self.main_w = int(self.screen_width * self.size_of_frame_relative_to_screen)
        self.main_h = int(self.screen_height * self.size_of_frame_relative_to_screen)

        self.canvas_w = self.main_w  # canvas and frame are the same size
        self.canvas_h = self.main_h
        self.video_canvas_w = self.canvas_w * self.size_of_video_relative_to_canvas
        self.video_canvas_h = self.canvas_h * self.size_of_video_relative_to_canvas

        self.canvas = tk.Canvas(self.master,width=self.canvas_w,height=self.canvas_h,bg=self.master.color_hex,
                                borderwidth=0,highlightthickness=0)
        self.video_canvas = tk.Canvas(self.canvas,width=self.video_canvas_w,height=self.video_canvas_h,
                                      bg=self.master.color_hex,borderwidth=0,highlightthickness=0)

        self.camera_frame_settings = CameraFrameSettings(self.master)

        self.state = False
        self.master.record=False

        self.registered_time_points = []

        self.create_time_point = tk.Button(self.canvas,width=13,text='Register time',bg=self.master.color_hex,
                                           borderwidth=0,highlightthickness=0,font=self.master.font,
                                           command=self.register_time_point)

        self.master.video = VideoCamera(self.master.recorded_video_directory_path)
        self.frame = self.master.video.get_frame()

        def key(event):
            if event.char == 'p' or event.char == ' ':
                self.master.video.pause = 1 - self.master.video.pause
            if event.char == 'f':
                self.toggle_fullscreen()

        self.master.bind("<Key>",key)

        self.ticker = 0

        self.frame_Image = Image.fromarray(self.frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        self.image_id = self.video_canvas.create_image(
            int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
            int((self.canvas_h * self.size_of_video_relative_to_canvas) / 2),
            image=self.frame)

        self.master.bind("<Escape>",self.end_fullscreen)

    def _pack(self):
        self.camera_frame_settings._pack()
        self.create_time_point.pack(side='bottom',anchor=tk.NE)  # should do only once
        self.canvas.pack(anchor=tk.N,expand=tk.YES)
        self.pack(side="left")

    def _unpack(self):
        self.camera_frame_settings._unpack()
        self.create_time_point.pack_forget()
        self.canvas.pack_forget()
        self.pack_forget()

    def _destroy(self):
        self.canvas.destroy()
        self.destroy()

    def canvas_size(self,width,height):  # input canvas size, not video canvas
        target_width = width * self.size_of_video_relative_to_canvas
        target_height = height * self.size_of_video_relative_to_canvas

        if target_width / target_height > self.master.video.aspect_ratio_:  # too wide: scale by the height
            video_frame_w = int(target_height / self.master.video.aspect_ratio_)
            video_frame_h = int(target_height)
        else:
            video_frame_h = int(target_width * self.master.video.aspect_ratio_)
            video_frame_w = int(target_width)
        return video_frame_w,video_frame_h

    def toggle_fullscreen(self,event=None):
        self.state = not self.state  # Just toggling the boolean
        self.master.attributes("-fullscreen",self.state)
        return "break"

    def end_fullscreen(self,event=None):
        self.state = False
        self.master.attributes("-fullscreen",False)
        sys.exit()

    def register_time_point(self):
        #time points are stored in seconds from the start of the recording
        recording_start = self.camera_frame_settings.recording_timestamp
        if recording_start is None:
            messagebox.showerror("Error","Start a recording before registering time points")
            return
        self.registered_time_points.append(
            (datetime.datetime.now() - recording_start).total_seconds())

        #updates the saved file if there is one.
        file_name = video_stem(self.master.video.path)
        pd.DataFrame(self.registered_time_points).to_csv(
            os.path.join(self.master.statistics_directory_path, file_name+ '_registered_time_points.csv'))

    def update(self,force=False):

        self.ticker+=1

        if self.ticker%12==0:
            self.camera_frame_settings.update_textbutton()
            self.camera_frame_settings.update_recording_length_textbutton()

        frame = self.master.video.get_frame()

        if self.master.record is True:
            self.master.video.save_frame(frame)

        self.frame_Image = Image.fromarray(frame)

        try:  # error only happens on program start
            self.frame_Image = self.frame_Image.resize((self.video_frame_w,
                                                        self.video_frame_h),
                                                       Image.Resampling.LANCZOS)
        except:
            self.video_frame_w,self.video_frame_h = self.canvas_size(self.canvas_w,self.canvas_h)

        self.frame = ImageTk.PhotoImage(self.frame_Image)

        self.video_canvas.itemconfig(self.image_id,image=self.frame)
