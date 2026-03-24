

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
import sys
from webcolors import rgb_to_hex
from tkinter import ttk as ttk
from webcolors import rgb_to_hex
import glob
from sys import platform

class Stabilize_Frame(tk.Frame):
    def __init__(self,master,*args,**kwargs):

        #super(Stabilize_Frame,self).__init__()

        self.top = tk.Toplevel()
        self.master = master

        self.screen_width = master.winfo_width()
        self.screen_height = master.winfo_height()

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

        self.canvas = tk.Canvas(self.top,width=self.canvas_w,height=self.canvas_h,bg=self.master.color_hex,
                                borderwidth=0,highlightthickness=0)

        self.ticker=0
        self.video_being_stabilized = None
        self.start_new_video = True
        self.path = self.master.recorded_video_directory_path
        self.master.videos_to_stabilize = self.check_which_items_are_stabilized()
        self.generate_stabilization_information_label()

    def generate_stabilization_information_label(self):
        self.stabilization_information_label = tk.Label(self.canvas,text='',borderwidth=0,bg=self.master.color_hex)


    def update_stabilization_information_label(self,t):
        if self.stabilization_information_label is not None:
            # t = str((datetime.datetime.now() - self.recording_timestamp).seconds)
            self.stabilization_information_label.config(text = t )
            self.stabilization_information_label.pack(anchor=tk.CENTER)
            #x = self.video_canvas_w / 20,y = self.video_canvas_h / 2)





    def check_which_items_are_stabilized(self):
        stabilized_items = self.get_items_from_path(self.path.replace('RecordedVideos','StabilizedVideos'))
        items = self.get_items_from_path(self.path)

        if platform == 'win32':
            a = [item.split('\\')[-1].split('.')[-2] for item in items]
            b = [item.split('\\')[-1].split('.')[-2] for item in stabilized_items]
        if platform == 'darwin':
            a = [item.split('/')[-1].split('.')[-2] for item in items]
            b = [item.split('/')[-1].split('.')[-2] for item in stabilized_items]

        return np.array(self.get_items_from_path(self.path))[np.invert(np.in1d(a,b))]

    def get_items_from_path(self,path):
        print(path+'/*.mp4')
        a =glob.glob(path+'/*.avi')
        a.extend(glob.glob(path + '/*.mp4'))
        try:
            for index,file_name in enumerate(a):
                os.rename(file_name,file_name.replace(',',''))
                a[index] = file_name.replace(',','')
        except:
            pass
        return a #needs to be updated if new formats are allowed



    def _pack(self):

        # self.settings_canvas.pack(side='right')
        # self.camera_frame_settings._pack()
        # self.participant_list._pack()

        self.canvas.pack(expand=tk.YES)
        self.pack(side="left")

    def _unpack(self):
        # self.fps_label.pack_forget()
        # self.participant_list._unpack()
        # self.camera_frame_settings._unpack()
        self.canvas.pack_forget()
        self.pack_forget()

    def _destroy(self):
        # self.participant_list._destroy()
        self.canvas.destroy()
        self.destroy()


    def update(self,force=False):

        self.ticker+=1
        t = ''

        if len(self.master.videos_to_stabilize)>0:
            if self.start_new_video:
                self.video_being_stabilized = VideoStabilization(path=self.master.videos_to_stabilize[0])
                self.start_new_video=False

            else:
                self.video_being_stabilized.update()
                if self.video_being_stabilized.current_stage=='finished':
                    self.start_new_video = True
                    self.master.videos_to_stabilize = self.check_which_items_are_stabilized()
                else:

                    t+='Current video being processed: \n'+str(self.master.videos_to_stabilize[0].split('/')[-1])+'\n\n'

                    if self.video_being_stabilized.current_stage == 'load':
                        t+= '\nLoad progress: ' + '\n' + str(self.video_being_stabilized.progress_load.output)
                    if self.video_being_stabilized.current_stage == 'transform':
                        t+='\nTransform progress: '+'\n'+str(self.video_being_stabilized.progress_transform.output)
                    if self.video_being_stabilized.current_stage == 'stabilize':
                        t+='\nStabilization progress: ' + '\n' + str(self.video_being_stabilized.progress_stabilize.output)
                    if self.video_being_stabilized.current_stage == 'finished':
                        t+='\nDone!'

                    t += '\n\nVideos remaining: \n' + str(len(self.master.videos_to_stabilize))

        else:
            t += '\n\nVideos remaining: \n' + str(len(self.master.videos_to_stabilize))

        self.update_stabilization_information_label(t)