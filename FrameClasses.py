import sys
if "Tkinter" not in sys.modules:
    import tkinter as tk
# from VideoCamera import VideoCamera
# from PlotFuns import drawPlot
import numpy as np
import pickle
from PIL import ImageTk,Image
import cv2
import time
from Caper import Video,ColorVideo,Rectangle,CrossCorrelation,EntryWithSet
import datetime
from Utilities import *

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler
import pandas as pd
import matplotlib.animation as animation
import random
from PIL import Image,ImageDraw,ImageFont
import matplotlib.colors as colors
import io

from pylab import rcParams
import glob
from webcolors import rgb_to_hex
from Caper import VideoCamera
import numpy as np
import os
from sys import platform
from Popup_Frame import Popup_Frame
from Save_Data_Popup import Save_Data_Popup
from Choose_Report_Popup import Choose_Report_Popup

class CameraFrameSettings(tk.Frame):
    def __init__(self,master,*args,**kwargs):
        super(CameraFrameSettings,self).__init__()
        self.master = master
        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()
        self. height =int(self.screen_width*1.0)
        self.width= int(self.screen_height * 0.1)

        self.size_of_icon = int(self.width*0.4)


        self.image_path = 'Source/NotRecording.png'

        self.recording_timestamp=None

        self.canvas = tk.Canvas(self.master,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)
        # self.canvas = tk.Canvas(self.master,width=self.width,height=self.height,bg='#4191C7',borderwidth=0,
        #                         highlightthickness=0)
        self.generate_recording_button()
        self.generate_textbutton()
        self.generate_recording_length_textbutton()


        # self.canvas.pack(side='left')


        self.canvas.bind("<Configure>",self._resize)
    def callback_capture(self):
        self.selected_tab = 'capture'
    def callback_analyze(self):
        self.selected_tab = 'analyze'
    def _resize(self,event):
        self.button.place_forget()
        self.label.place_forget()
        self.fps_label.place_forget()
        # self.button.destroy()

        self.screen_width= event.width
        self.screen_height = event.height

        self.height = int(self.screen_width * 1.0)
        self.width = int(self.screen_height * 0.2)
        self.size_of_icon = int(self.height * 0.4)
        # self.generate_recording_button()
        self.button.place(x=self.width/20,y=self.height/2+10)
        self.label.place(x=self.width / 20,y=self.height / 2 + 50)

        self.fps_label.place(x=self.width/20,y=self.height/2-10)

        self.recording_length_label.place(x=self.width / 20,y=self.height / 2 + 85)

    def toggle(self):
        if self.master.record:
            self.image_path = 'Source/NotRecording.png'
            self.recording_timestamp=None
            self.recording_length_label.place_forget()
            # self.recording_length_label.destroy()
            self.master.video.destroy_writer()
            self.master.record = False
        else:
            self.image_path = 'Source/Recording.png'
            self.recording_timestamp = datetime.datetime.now()
            # self.fps_label.place(x=self.width / 20,y=self.height / 2 - 10)
            self.recording_length_label.place(x=self.width / 20,y=self.height / 2 + 85)
            
            self.master.video = VideoCamera(self.master.recorded_video_directory_path)
            self.master.record = True

        self.generate_recording_button()


    def generate_textbutton(self):
        self.fps_label = tk.Label(self.canvas,text='',borderwidth=0,bg=self.master.color_hex)
        self.fps_label.place(x=self.width/20,y=self.height/2-10)

    def update_textbutton(self):
        self.fps_label.config(text='FPS: '+str(int(self.master.fps)))

    def generate_recording_length_textbutton(self):
        self.recording_length_label = tk.Label(self.canvas,text='',borderwidth=0,bg=self.master.color_hex)
        # self.recording_length_label.place(x=self.width / 20,y=self.height / 2 + 85)

    def update_recording_length_textbutton(self):
        if self.recording_timestamp is not None:
            t = str((datetime.datetime.now() - self.recording_timestamp).seconds)
            self.recording_length_label.config(text='Time: ' + t)


    def _unpack(self):
        self.canvas.pack_forget()
    def _pack(self):
        self.canvas.pack(side='right')
    def _destroy(self):
        self.master.video.destroy_writer()
        self.canvas.destroy()


    def update(self):
        pass

    def generate_recording_button(self):
        temp_img = Image.open(self.image_path) #Source/logo_small.png
        temp_img = temp_img.resize((int(self.size_of_icon),int(self.size_of_icon)),Image.Resampling.LANCZOS)
        blank_image = Image.new('RGBA',(self.size_of_icon,self.size_of_icon),self.master.color_rgb)
        blank_image.paste(temp_img,mask=temp_img)
        r,g,b,a = cv2.split(np.array(blank_image))

        temp_img = Image.fromarray(cv2.merge((r,g,b)))
        self.icon = ImageTk.PhotoImage(temp_img)
        self.button = tk.Button(self.canvas,width=self.size_of_icon,height=self.size_of_icon,bg=self.master.color_hex,image=self.icon,borderwidth=0,command=self.toggle)
        self.label = tk.Label(self.canvas,bg=self.master.color_hex,text='Record',font=self.master.font)

        # self.button.pack()
        self.button.place(x=self.width/20,y=self.height/2+10)
        self.label.place(x=self.width/20,y=self.height/2+50)

class Menu(tk.Frame):
    def __init__(self,master,*args,**kwargs):
        super(Menu,self).__init__()
        self.master = master
        self.screen_width = self.master.width
        self.screen_height = self.master.height
        self.width =int(self.screen_width*0.07)
        self.height = int(self.screen_height * 1.0)
        self.size_of_logos = int(self.width*0.9)


        self.master.selected_tab = 'analyze'
        # self.previously_selected_tab = 'capture'
        # self.canvas =

        self.canvas = tk.Canvas(self.master,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)


        logotype_size = self.size_of_logos
        temp_img = Image.open('Source/Capture-Logo.png')
        temp_img = temp_img.resize((int(logotype_size ),int(logotype_size )),Image.Resampling.LANCZOS)
        blank_image = Image.new('RGBA',(logotype_size,logotype_size ),self.master.color_rgb)
        blank_image.paste(temp_img,mask=temp_img)
        r,g,b,a = cv2.split(np.array(blank_image))

        temp_img = Image.fromarray(cv2.merge((r,g,b)))
        self.logotype = ImageTk.PhotoImage(temp_img)
        #self.button = tk.Button(self.canvas,width=self.size_of_icon,height=self.size_of_icon,bg=self.master.color_hex,image=self.icon,borderwidth=0,command=self.toggle)
        self.logotype_label = tk.Label(self.canvas,bg=self.master.color_hex,image=self.logotype)




        temp_img = Image.open('Source/Capture3.png') #Source/logo_small.png
        temp_img = temp_img.resize((int(self.size_of_logos),int(self.size_of_logos)),Image.Resampling.LANCZOS)
        blank_image = Image.new('RGBA',(self.size_of_logos,self.size_of_logos),self.master.color_rgb)
        blank_image.paste(temp_img,mask=temp_img)
        r,g,b,a = cv2.split(np.array(blank_image))
        temp_img = Image.fromarray(cv2.merge((r,g,b)))
        self.icon_capture = ImageTk.PhotoImage(temp_img)

        temp_img = Image.open('Source/Analyze.png') #Source/logo_small.png
        temp_img = temp_img.resize((int(self.size_of_logos),int(self.size_of_logos)),Image.Resampling.LANCZOS)
        blank_image = Image.new('RGBA',(self.size_of_logos,self.size_of_logos),self.master.color_rgb)
        blank_image.paste(temp_img,mask=temp_img)
        r,g,b,a = cv2.split(np.array(blank_image))
        temp_img = Image.fromarray(cv2.merge((r,g,b)))
        self.icon_analyze = ImageTk.PhotoImage(temp_img)

        # temp_img = Image.open('Source/Stabilize.png') #Source/logo_small.png
        # temp_img = temp_img.resize((int(self.size_of_logos),int(self.size_of_logos)),Image.Resampling.LANCZOS)
        # blank_image = Image.new('RGBA',(self.size_of_logos,self.size_of_logos),self.master.color_rgb)
        # blank_image.paste(temp_img,mask=temp_img)
        # r,g,b,a = cv2.split(np.array(blank_image))
        # temp_img = Image.fromarray(cv2.merge((r,g,b)))
        # self.icon_stabilize = ImageTk.PhotoImage(temp_img)

        temp_img = Image.open('Source/Stabilize.png') #Source/logo_small.png
        temp_img = temp_img.resize((int(self.size_of_logos),int(self.size_of_logos)),Image.Resampling.LANCZOS)
        blank_image = Image.new('RGBA',(self.size_of_logos,self.size_of_logos),self.master.color_rgb)
        blank_image.paste(temp_img,mask=temp_img)
        r,g,b,a = cv2.split(np.array(blank_image))
        temp_img = Image.fromarray(cv2.merge((r,g,b)))
        self.icon_flow= ImageTk.PhotoImage(temp_img)



        # self.plot_id = self.plot_canvas.create_image(int(self.plot_canvas_w * 0.5),int(self.plot_canvas_h * 0.5),
        #                                              image=self.plot_image)



        # self.img = self.img.resize((int(self.width),int(self.height)),Image.Resampling.LANCZOS)


        # self.plot_image = Image.fromarray(cv2.merge((r,g,b)))


        # self.img = ImageTk.PhotoImage(self.img)

        # self.image_id = self.canvas.create_image(int(self.width/2),int(self.height/2),image=self.img)

        # self.canvas.itemconfig(self.image_id,image=self.img)


        self.capture_button=tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Capture',image=self.icon_capture,borderwidth=0, highlightthickness=0,command=self.callback_capture)
        self.analyze_button = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Analyze',image=self.icon_analyze,borderwidth=0,highlightthickness=0,command=self.callback_analyze)
        # self.stabilize_button = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Stabilize',image=self.icon_stabilize,borderwidth=0,highlightthickness=0,command=self.callback_stabilize)
        self.flow_button = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Flow',image=self.icon_flow,borderwidth=0,highlightthickness=0,command=self.callback_flow)

        self.capture_label = tk.Label(self.canvas,text='Capture',font = self.master.font)
        self.analyze_label = tk.Label(self.canvas,text='Analyze',font=self.master.font)
        # self.stabilize_label = tk.Label(self.canvas,text='Stabilize',font=self.master.font)
        self.flow_label = tk.Label(self.canvas,text='Flow',font=self.master.font)


        # c = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Click Me !',image=self.img,
        #               borderwidth=0,highlightthickness=0)
        # d = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Click Me !',image=self.img,
        #               borderwidth=0,highlightthickness=0)
        # b=tk.Button(self.master,width=300,height=300,text='Click Me !',image=self.img)

        offset_icon = self.size_of_logos
        offset_text = 75
        original_height = int(self.height / 5)
        offset_width  =int(self.width * 0.05)

        self.logotype_label.place(x=offset_width,y=0 )
        self.capture_label = tk.Label(self.canvas,text='Capture',font = self.master.font,bg=self.master.color_hex)
        self.capture_button.place(x=offset_width,y=original_height + (offset_icon * 0)+(offset_text*0))
        self.capture_label.place(x=offset_width+1,y=original_height + (offset_icon * 0)+(offset_text*1))
        self.analyze_label = tk.Label(self.canvas,text='Analyze',font=self.master.font,bg=self.master.color_hex)
        self.analyze_button.place(x=offset_width,y=original_height + (offset_icon * 1) + (offset_text * 1))
        self.analyze_label.place(x=offset_width+3,y=original_height + (offset_icon * 1)+(offset_text*2))
        # self.stabilize_label = tk.Label(self.canvas,text='Stabilize',font=self.master.font,bg=self.master.color_hex)
        # self.stabilize_button.place(x=offset_width,y=original_height+(offset_icon*2)+(offset_text*2))
        # self.stabilize_label.place(x=offset_width,y=original_height + (offset_icon * 2)+(offset_text*3))
        self.flow_label = tk.Label(self.canvas,text='Flow',font=self.master.font,bg=self.master.color_hex)
        self.flow_button.place(x=offset_width,y=original_height+(offset_icon*2)+(offset_text*2))
        self.flow_label.place(x=offset_width+11,y=original_height + (offset_icon * 2)+(offset_text*3))

        # b.pack(anchor=tk.W)
        # c.pack(anchor=tk.W)



    def _pack(self):
        self.canvas.pack(side='left')

    def _unpack(self):
        self.canvas.pack_forget()

    def _destroy(self):
        self.canvas.destroy()

        # self.canvas.bind("<Configure>",self._resize)
    def callback_capture(self):
        self.master.selected_tab = 'capture'
    def callback_analyze(self):
        self.master.selected_tab = 'analyze'
    # def callback_stabilize(self):
    #     self.master.selected_tab = 'stabilize'
    def callback_flow(self):
        self.master.selected_tab = 'flow'


    def _resize(self,event):
        self.screen_width  = event.width
        self.screen_height = event.height

        # self.screen_width = master.winfo_screenwidth()
        # self.screen_height = master.winfo_screenheight()
        self.width = int(self.screen_width * 0.02)
        self.height = int(self.screen_height * 0.7)
        # b.destroy()
        # b=tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Click Me !',image=self.img,borderwidth=0, highlightthickness=0)
        # c = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Click Me !',image=self.img,
        #               borderwidth=0,highlightthickness=0)
        # d = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Click Me !',image=self.img,
        #               borderwidth=0,highlightthickness=0)
        # b=tk.Button(self.master,width=300,height=300,text='Click Me !',image=self.img)

        # self.capture_button.place(x=0, y=self.height/2)

        #b.place(x=0, y=self.height/2)

        #
        # self.canvas.create_window(0,0,window=self.canvas)
        # self.canvas.itemconfig(self.image_id,image=self.img)

        # b = tk.Label(self.canvas,image=self.img,text='jeasdasd',font=("Helvetica",10),anchor=tk.CENTER,compound=tk.RIGHT,
        #              justify=tk.RIGHT,pady=5,bg=self.master.color_hex,borderwidth=2,relief='groove')
        # self.canvas.pack(side='left')

    def update(self):
        # self.draw_canvas.create_window(0,0,window=self.canvas)
        # self.draw_canvas.itemconfig(self.image_id,image=self.img)
        #
        # self.draw_canvas.pack()
        pass

    def _resize(self):
        #should be handled by resizing canvas? at least if we call update after resize, right?
        pass

class MatplotlibFrame(tk.Frame):
    def __init__(self,master,*args,**kwargs):
        super(MatplotlibFrame,self).__init__()
        self.master = master

        # self.plot_canvas_w = int(self.canvas_w*0.1)
        # self.plot_canvas_h = int(self.canvas_h*0.1)
        # self.plot_canvas= tk.Canvas(self.master,width=self.plot_canvas_w,height=self.plot_canvas_h)
        # self.plot_canvas.pack(side="bottom")

        self.screen_width = master.winfo_screenwidth()
        self.screen_height = master.winfo_screenheight()
        self.plot_canvas_w = int(self.screen_width*0.1)
        self.plot_canvas_h = int(self.screen_height*0.1)

        self.plot_canvas = tk.Canvas(self.master,width=self.plot_canvas_w,height=self.plot_canvas_h,borderwidth=0, highlightthickness=0)
        # self.plot_canvas.pack(side='left')
        self.fig = plt.figure(figsize=(1,1*self.master.video.aspect_ratio_))
        self.ax = self.fig.add_subplot(111)
        self.continous_plot_length = 25
        self.continous_plot = plt.scatter(x=np.arange(0,self.continous_plot_length),
                                          y=[random.uniform(0,1) for i in range(self.continous_plot_length)],
                                          c=[random.uniform(0,1) for i in range(self.continous_plot_length)],
                                          cmap='coolwarm',s=5)

        self.fig.gca().axes.xaxis.set_ticklabels([])
        self.fig.gca().axes.yaxis.set_ticklabels([])
        self.ax.axis('off')


        buf = io.BytesIO()
        self.fig.savefig(buf,format='png',transparent=True,bbox_inches = 'tight')
        buf.seek(0)
        buf_image = Image.open(buf)

        buf_image = buf_image.resize((int(self.plot_canvas_w),int(self.plot_canvas_h)),Image.Resampling.LANCZOS)

        blank_image = Image.new('RGBA',(self.plot_canvas_w,self.plot_canvas_h),self.master.color_rgb)
        blank_image.paste(buf_image,mask=buf_image)


        r,g,b,a = cv2.split(np.array(blank_image))
        self.plot_image = Image.fromarray(cv2.merge((r,g,b)))
        self.plot_image = ImageTk.PhotoImage(self.plot_image)
        self.plot_id = self.plot_canvas.create_image(int(self.plot_canvas_w * 0.5),int(self.plot_canvas_h * 0.5),
                                                     image=self.plot_image)


    def _resize_video_canvas(self,event):
        self.master.create_window(int((self.plot_canvas_w) * 0.2),int((self.plot_canvas_h) * 0.9),window=self.plot_canvas,borderwidth=0, highlightthickness=0)
        self.plot_id = self.plot_canvas.create_image(int(self.plot_canvas_w*0.5),int(self.plot_canvas_h*0.5),image=self.plot_image)
    def _pack(self):
        self.plot_canvas.pack()
        # self.main_frame.create_window(0,0,window=self.matplotlib_frame)
    def _unpack(self):
        self.plot_canvas.pack_forget()
    def _destroy(self):
        self.plot_canvas.destroy()
        self.destroy()
    def update(self):
        # print('matplotlib')

            # self.blur_vector[self.master.video.get_frame_number()] = calculate_blur(frame)


        if self.master.video.get_frame_number()%1==0:

            if self.master.video.get_frame_number()>self.continous_plot_length:


                a = self.master.video.blur_vector[:self.master.video.get_frame_number()]

                b = np.array(a[self.master.video.get_frame_number() - self.continous_plot_length:self.master.video.get_frame_number()])
                c=b
                c[c>np.mean(np.mean(a[a!=0]))] = 1
                c[c <= np.mean(np.mean(a[a != 0]))] = 0
                d = a[a!=0]

                self.continous_plot.set_offsets(np.array(list(zip(range(0,self.continous_plot_length),
                                                                  self.master.video.blur_vector[
                                                                  self.master.video.get_frame_number() - self.continous_plot_length:self.master.video.get_frame_number()]))))
                self.continous_plot.set_array(c)

                plt.ylim(0.007,0.009)
                buf = io.BytesIO()
                self.fig.savefig(buf,format='png',transparent=True,bbox_inches = 'tight')
                buf.seek(0)
                buf_image = Image.open(buf)

                buf_image = buf_image.resize((int(self.plot_canvas_w),int(self.plot_canvas_h)),
                                             Image.Resampling.LANCZOS)
                blank_image = Image.new('RGBA',(self.plot_canvas_w,self.plot_canvas_h),self.master.color_rgb)
                blank_image.paste(buf_image,mask=buf_image)


                r,g,b,a = cv2.split(np.array(blank_image))
                self.plot_image = Image.fromarray(cv2.merge((r,g,b)))
                self.plot_image = ImageTk.PhotoImage(self.plot_image)

                self.plot_canvas.itemconfig(self.plot_id,image=self.plot_image)



class VideoFrame(tk.Frame):
    def __init__(self,master,path,*args,**kwargs):
        super(VideoFrame, self).__init__()
        # tk.Frame.__init__(self,master,*args,**kwargs)
        self.master = master

        # print(master.winfo_screenwidth(),master.winfo_screenheight())

        # prefered_size = (1000,700)

        # self.screen_width = master.winfo_screenwidth()
        # self.screen_height=master.winfo_screenheight()
        #

        # self.screen_width = 1000
        # self.screen_height=700

        self.size_of_frame_relative_to_screen = 0.7
        self.size_of_video_relative_to_canvas = 1.0



        self.image = None
        self.ctrl_and_mouse_click_flag=0
        self.state=False
        self.video_bar_click_x_coordinate=None

        self.canvas_w = int(self.master.width*self.size_of_frame_relative_to_screen)
        self.canvas_h = int(self.master.height*self.size_of_frame_relative_to_screen)
        self.video_canvas_w = self.canvas_w*self.size_of_video_relative_to_canvas
        self.video_canvas_h = self.canvas_h* self.size_of_video_relative_to_canvas

        self.video_bar_relative_to_canvas = 0.02
        self.size = (self.canvas_w,self.canvas_h)

        self.click_x=0
        self.click_y=0

        self.registered_time_points = []

        self.canvas = tk.Canvas(self.master,width=self.canvas_w,height=self.canvas_h,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)
        self.video_canvas= tk.Canvas(self.canvas,width=self.video_canvas_w ,height=self.video_canvas_h,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)

        self.video_bar_w=self.video_canvas_w
        self.video_bar_h=int(self.video_canvas_h*self.video_bar_relative_to_canvas)
        self.video_bar = tk.Canvas(self.canvas,width=self.video_canvas_w,height=int(self.video_canvas_h * self.video_bar_relative_to_canvas),borderwidth=0,highlightthickness=0) #self.master.color_hex

        self.set_video(path)
        self.frame = self.master.video.get_frame()
        self.master.video.set_frame(0)

        self.save_data_button = tk.Button(self.canvas,width=13,text='Save data',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,font=self.master.font,command=self.save_data)
        self.generate_report_button= tk.Button(self.canvas,width=13,text='Generate report',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,font=self.master.font,command=self.generate_report)
        self.create_time_point = tk.Button(self.canvas,width=13,text='Register time',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,font=self.master.font,command=self.register_time_point)



        self.rectangle_width_entry = EntryWithSet(self.canvas,width=20,text='',bg=self.master.color_hex,borderwidth=0, highlightthickness=0,font=self.master.font,justify=tk.RIGHT)
        self.rectangle_height_entry = EntryWithSet(self.canvas,width=20,text='',bg=self.master.color_hex,borderwidth=0, highlightthickness=0,font=self.master.font,justify=tk.RIGHT)
        self.rectangle_width_entry.set('Width: 12')
        self.rectangle_height_entry.set('Height: 12')

        self.video_time= EntryWithSet(self.canvas,width=20,text='',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,font=self.master.font,justify=tk.RIGHT)
        self.cross_correlation_estimation_entry = EntryWithSet(self.canvas,width=20,text='',bg=self.master.color_hex,borderwidth=0,
                                       highlightthickness=0,font=self.master.font,justify=tk.RIGHT)
        #
        #
        # self.frame_Image = Image.fromarray(self.frame)
        # self.frame = ImageTk.PhotoImage('Source/Capture-Logo.png')

        # #HERE I REMOVED OSKAR
        # self.image_id = self.video_canvas.create_image(int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
        #                                                int((self.canvas_h * self.size_of_video_relative_to_canvas) / 2),
        #                                                image=self.frame)

        # self.rectangle2_width_entry.configure(text='ej')
        # self.rectangle1_width_entry.pack(anchor=tk.NE)
        # self.rectangle2_width_entry.pack(anchor=tk.SE)

        # self.rectangle1_width_entry.place(x=self.master.width*0.5,y=0)
        # self.rectangle2_width_entry.place(x=self.master.width*0.5,y=self.master.height*0.8)



        def callback_video_bar(event):
            self.master.video.set_frame(int((event.x/self.video_bar_w)*self.master.video.number_of_frames_))
            self.update(force=True)
            self.generate_progress_bar()



        def callback(event):

            #scale so that it's returned in percentage of display

            linear_map_width = self.video_canvas_w/self.master.video.width_
            linear_map_height = self.video_canvas_h / self.master.video.height_

            self.click_x = int(event.x / linear_map_width)
            self.click_y = int(event.y / linear_map_height)

            if platform =='win32':
                k = [8,12]
            if platform == 'darwin':
                k = [4,6]

            if self.master.current_key in k: #control button (ctrl):
                self.rectangle2.set_clicks(self.click_x,self.click_y)
            else:
                self.rectangle1.set_clicks(self.click_x,self.click_y)



        # def callback_release(event):
        #

        # self.master.bind("<Key>",key)
        # self.master.bind("<KeyRelease>",key_release)

        self.video_canvas.bind("<Button-1>",callback)
        # self.video_canvas.bind("<ButtonRelease-1>",callback_release)

        self.video_bar.bind("<Button-1>",callback_video_bar)

        # self.delay = 0

        self.previous_frame = self.frame
        self.frame_Image = Image.fromarray(self.frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        #HERE I REMOVED OSKAR
        self.image_id = self.video_canvas.create_image(int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
                                                       int((self.canvas_h * self.size_of_video_relative_to_canvas) / 2),
                                                       image=self.frame)
        # self.video_bar_image_id = self.video_bar.create_image(
        #     int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
        #     int(self.video_bar_h / 2),
        #     image = self.bar)
        self.generate_progress_bar()
        self._resize()

    def _pack(self):
        self.generate_report_button.pack(side='bottom',anchor=tk.NE)  # should do only once
        self.save_data_button.pack(side='bottom',anchor=tk.NE)  # should do only once
        self.create_time_point.pack(side='bottom',anchor=tk.NE)  # should do only once
        self.rectangle_width_entry.pack(anchor=tk.NE)
        self.rectangle_height_entry.pack(anchor=tk.NE)
        self.video_time.pack(anchor=tk.NE)
        self.cross_correlation_estimation_entry.pack(anchor=tk.NE)
        self.video_bar.pack(side='bottom')
        self.video_canvas.pack(anchor=tk.CENTER)
        self.canvas.pack(anchor=tk.N,expand=tk.YES)
        self.pack(anchor=tk.CENTER)

    def _unpack(self):
        self.generate_report_button.pack_forget()  # should do only once
        self.save_data_button.pack_forget()
        self.rectangle_width_entry.pack_forget()
        self.rectangle_height_entry.pack_forget()
        self.create_time_point.pack_forget()
        self.video_time.pack_forget()
        self.cross_correlation_estimation_entry.pack_forget()
        self.video_canvas.pack_forget()
        self.canvas.pack_forget()
        self.pack_forget()
    def _destroy(self):
        self.video_canvas.destroy()
        self.canvas.destroy()
        self.destroy()

    def generate_progress_bar(self,percentage=None):



        width = int(self.video_bar_w)
        height = int(self.canvas_h * self.video_bar_relative_to_canvas)
        bar_color = [91,91,91]
        bar_fill_color=[204,0,1]
        time_point_color = [255,255,255]

        if percentage is not None:
            progress_percent=percentage
        else:
            progress_percent = (self.master.video.get_frame_number()) / (self.master.video.number_of_frames_)

        bar = np.zeros([height,width,3])

        bar[:,:,0] = bar_color[0]
        bar[:,:,1] = bar_color[1]
        bar[:,:,2] = bar_color[2]

        bar[:,:int(progress_percent*width),0] = bar_fill_color[0]
        bar[:,:int(progress_percent * width),1] = bar_fill_color[1]
        bar[:,:int(progress_percent * width),2] = bar_fill_color[2]


        time_points = self.registered_time_points
        if len(time_points)>0:
            for time_point in time_points:
                time_point_percent =(time_point*30) / (self.master.video.number_of_frames_)

                bar[:,int(time_point_percent *width)-1:int(time_point_percent *width)+1,0] = time_point_color[0]
                bar[:,int(time_point_percent * width) - 1:int(time_point_percent * width) + 1,1] = time_point_color[1]
                bar[:,int(time_point_percent * width) - 1:int(time_point_percent * width) + 1,2] = time_point_color[2]



        bar = cv2.merge((bar[:,:,0],bar[:,:,1],bar[:,:,2]))

        bar = Image.fromarray(bar.astype(np.uint8))
        self.bar = ImageTk.PhotoImage(bar)
        self.video_bar_image_id = self.video_bar.create_image(int(self.video_canvas_w / 2),int(self.video_bar_h / 2),
                                                              image=self.bar)

    def canvas_size(self,width,height): #input canvas size, not video canvas
        target_width = width * self.size_of_video_relative_to_canvas
        target_height = height * self.size_of_video_relative_to_canvas

        if target_width / target_height > self.master.video.aspect_ratio_:  # för bred, använd höjden för att skala
            video_frame_w = int(target_height / self.master.video.aspect_ratio_)
            video_frame_h = int(target_height)
        else:
            video_frame_h = int(target_width * self.master.video.aspect_ratio_)
            video_frame_w = int(target_width)
        return video_frame_w,video_frame_h

    def _resize(self,event=None):

        # print('vidframe'+str(self.canvas_w)+' '+str(self.canvas_h))

        self.canvas_w = int(self.master.width*self.size_of_frame_relative_to_screen)
        self.canvas_h = int(self.master.height*self.size_of_frame_relative_to_screen)

        self.plot_canvas_w = int(self.canvas_w*0.1)
        self.plot_canvas_h = int(self.canvas_h*0.1)
        self.video_canvas_w,self.video_canvas_h = self.canvas_size(self.canvas_w,self.canvas_h)

        print('v '+str(self.video_canvas_w)+' '+str(self.video_canvas_h))
        # self.canvas.configure(width=self.canvas_w,height=self.canvas_h)

        self.video_canvas.configure(width=self.video_canvas_w,height=self.video_canvas_h)
        self.canvas.create_window(int((self.canvas_w) / 2),int((self.canvas_h) / 2),window=self.video_canvas)
        #
        self.image_id = self.video_canvas.create_image(self.video_canvas_w/2,self.video_canvas_h/2,image=self.frame)

        self.video_bar_h = int(self.video_canvas_h * self.video_bar_relative_to_canvas)
        self.video_bar_w = self.video_canvas_w

        self.video_bar.configure(width=self.video_canvas_w,height=self.video_bar_h)
        #
        self.canvas.create_window(int((self.canvas_w) / 2),int(self.canvas_h/2)+int(self.video_canvas_h / 2),window=self.video_bar)

        self.generate_progress_bar()

        # print('vidframe' + str(self.canvas_w) + ' ' + str(self.canvas_h))










    def set_video(self,path):

        self.click_x=0
        self.click_y=0

        self.master.video = Video(path) # need 2 remove
        frame = self.master.video.get_frame()
        self.frame_Image = Image.fromarray(frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        self.image = None
        self.ctrl_and_mouse_click_flag = 0
        self.state = False
        self.video_bar_click_x_coordinate = None

        try:
            self.registered_time_points = list(pd.read_csv(path.replace('StabilizedVideos','Statistics').replace('RecordedVideos','Statistics')[:-4]+'_registered_time_points.csv')['0'].values)
            print('success')

        except:
            self.registered_time_points=[]

        self.master.blur_vector = np.zeros([self.master.video.number_of_frames_])

        self.master.current_key = 0
        self.rectangle1 = Rectangle(isForward=True)
        self.rectangle2 = Rectangle(isForward=False)

        self.cross_correlation = CrossCorrelation(self.master.video,self.rectangle1,self.rectangle2)

        self.video_bar_w = self.video_canvas_w
        self.video_bar_h = int(self.video_canvas_h * self.video_bar_relative_to_canvas)


        self.generate_progress_bar()

        #HERE I REMOVE OSKAR
        # self.image_id = self.video_canvas.create_image(int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
        #                                                int((self.canvas_h * self.size_of_video_relative_to_canvas) / 2),
        #                                                image=self.frame)

        self.video_bar_image_id = self.video_bar.create_image(
            int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
            int(self.video_bar_h / 2),
            image = self.bar)

        # self._resize()
        self.master.video.set_frame(0)
        self.master.video.pause = 1


        self.written_csvs = 0

    def get_rectangle_width_and_height(self):
        try:
            s = self.rectangle_height_entry.get()
            h=[int(s) for s in s.split() if s.isdigit()][0]
            # self.rectangle_height_entry.set('Height: '+str(h))
            s = self.rectangle_width_entry.get()
            w=[int(s) for s in s.split() if s.isdigit()][0]
            # self.rectangle_width_entry.set('Width: ' + str(w))
            self.rectangle1.set_width_and_height(w,h)
            self.rectangle2.set_width_and_height(w,h)

        except:
            pass

    def save_data(self):

        if self.cross_correlation.check_if_enough_data_for_report():

            self.master.save_report_name = ''
            print(self.master.save_report_name)
            self.popup = Save_Data_Popup(self.master)
            self.master.wait_window(self.popup.top)
            print(self.master.save_report_name)



            if platform == 'win32':
                file_name = self.master.video.path.split('\\')[-1][:-4]
            if platform == 'darwin':
                file_name = self.master.video.path.split('/')[-1][:-4]


            pd.DataFrame(self.cross_correlation.get_mean_intensity()).to_csv(
                os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___cross_correlation.csv'))
            pd.DataFrame(self.master.blur_vector).to_csv(
                os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___blur_vector.csv'))
            pd.DataFrame(self.cross_correlation.distance_vector).to_csv(
                os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___distance_vector.csv'))
            pd.DataFrame(self.registered_time_points).to_csv(
                os.path.join(self.master.statistics_directory_path,file_name+'_registered_time_points.csv'))


        else:
            tk.messagebox.showerror("Error", "Not enought data to save yet")

    def register_time_point(self):
        self.registered_time_points.append(self.frame_number/30)

    def generate_report(self):

        file_name=''

        if platform == 'win32':
            file_name = self.master.video.path.split('\\')[-1][:-4]
        if platform == 'darwin':
            file_name = self.master.video.path.split('/')[-1][:-4]


        a = glob.glob(os.path.join(self.master.statistics_directory_path,file_name) + '___*___cross_correlation.csv')

        if len(a)>0:
            list_of_reports=[]
            for item in a:
                #file_path = os.path.basename(item).split('___')[0]
                print(item)
                print(os.path.basename(item).split('___'))
                report_name = os.path.basename(item).split('___')[1]
                list_of_reports.append(report_name)

            self.master.chosen_report_to_generate=''

            self.popup = Choose_Report_Popup(self.master,list_of_reports)
            self.master.wait_window(self.popup.top)

            if os.path.isfile(os.path.join(self.master.statistics_directory_path,file_name + '___' +self.master.chosen_report_to_generate + '___distance_vector.csv')) and \
                os.path.isfile(os.path.join(self.master.statistics_directory_path,file_name + '___' +self.master.chosen_report_to_generate + '___cross_correlation.csv')) and \
                os.path.isfile(os.path.join(self.master.statistics_directory_path,file_name + '___' +self.master.chosen_report_to_generate + '___blur_vector.csv')):

                self.cross_correlation.generate_report(os.path.join(self.master.statistics_directory_path,file_name + '___' +self.master.chosen_report_to_generate),self.registered_time_points)
            else:
                tk.messagebox.showerror("Error","There is no saved data, save data first in order to create a report")
        else:
            tk.messagebox.showerror("Error","There are no saved reports")

    def update(self,force=False,stop=False):

        if stop is False:
            self.frame_number = self.master.video.get_frame_number()




            if self.frame_number % 5 == 0:
                self.get_rectangle_width_and_height()
                self.video_time.set('Time: ' + str(int(self.frame_number / 30))+'s')

            if self.frame_number % 20 == 0:
                cross_correlation_estimation=self.cross_correlation.estimate_cross_correlation(self.frame_number)
                self.cross_correlation_estimation_entry.set('Correlation: ' + cross_correlation_estimation)
                print(cross_correlation_estimation)

            if self.frame_number%5==0:
                self.generate_progress_bar()
                # self.video_bar.itemconfig(self.video_bar_image_id,image=self.bar)

            if self.master.video.pause == 0 or force==True:
                # print('update')

                frame = self.master.video.get_frame()
                self.previous_frame = frame

                if frame is not None:
                    # print(frame)

                    frame = self.rectangle1.draw_rectangle(frame)
                    frame = self.rectangle2.draw_rectangle(frame)


                    self.cross_correlation.set_cropped_frame_data(self.frame_number,
                                                                  self.rectangle1.get_selected_data(),
                                                                  self.rectangle2.get_selected_data())

                    self.cross_correlation.calculate_distance(self.frame_number)

                    self.master.blur_vector[self.frame_number] = calculate_blur(frame)



                    self.frame_Image = Image.fromarray(frame)
                    self.frame_Image = self.frame_Image.resize((self.video_canvas_w,self.video_canvas_h),Image.Resampling.LANCZOS)


                    self.frame = ImageTk.PhotoImage(self.frame_Image)


                    self.video_canvas.itemconfig(self.image_id,image=self.frame)


            else:
                frame = self.rectangle1.draw_rectangle(self.previous_frame)
                frame = self.rectangle2.draw_rectangle(frame)
                frame_Image = Image.fromarray(frame)
                # self.video_frame_w,self.video_frame_h = self.canvas_size(self.canvas_w,self.canvas_h)
                frame_Image = frame_Image.resize((self.video_canvas_w,self.video_canvas_h),Image.Resampling.LANCZOS)
                self.frame = ImageTk.PhotoImage(frame_Image)
                self.video_canvas.itemconfig(self.image_id,image=self.frame)
                pass

            if self.master.video.finished:


                self.generate_progress_bar(1.0)
                # self.video_bar.itemconfig(self.video_bar_image_id,image=self.bar)

                # self.generate_progress_bar()





class FlowFrame(tk.Frame):
    def __init__(self,master,path,*args,**kwargs):
        super(FlowFrame, self).__init__()
        # tk.Frame.__init__(self,master,*args,**kwargs)
        self.master = master

        # print(master.winfo_screenwidth(),master.winfo_screenheight())

        # prefered_size = (1000,700)

        # self.screen_width = master.winfo_screenwidth()
        # self.screen_height=master.winfo_screenheight()
        #

        # self.screen_width = 1000
        # self.screen_height=700

        self.size_of_frame_relative_to_screen = 0.7
        self.size_of_video_relative_to_canvas = 1.0



        self.image = None
        self.ctrl_and_mouse_click_flag=0
        self.state=False
        self.video_bar_click_x_coordinate=None

        self.canvas_w = int(self.master.width*self.size_of_frame_relative_to_screen)
        self.canvas_h = int(self.master.height*self.size_of_frame_relative_to_screen)
        self.video_canvas_w = self.canvas_w*self.size_of_video_relative_to_canvas
        self.video_canvas_h = self.canvas_h* self.size_of_video_relative_to_canvas

        self.video_bar_relative_to_canvas = 0.02
        self.size = (self.canvas_w,self.canvas_h)

        self.click_x=0
        self.click_y=0
        self.clickevent = (0,0)
        self.releaseevent = (10,10)

        self.canvas = tk.Canvas(self.master,width=self.canvas_w,height=self.canvas_h,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)
        self.video_canvas= tk.Canvas(self.canvas,width=self.video_canvas_w ,height=self.video_canvas_h,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)

        self.video_bar_w=self.video_canvas_w
        self.video_bar_h=int(self.video_canvas_h*self.video_bar_relative_to_canvas)
        self.video_bar = tk.Canvas(self.canvas,width=self.video_canvas_w,height=int(self.video_canvas_h * self.video_bar_relative_to_canvas),borderwidth=0,highlightthickness=0) #self.master.color_hex

        self.set_video(path)
        self.frame = self.master.video.get_frame()
        self.master.video.set_frame(0)


        self.save_data_button = tk.Button(self.canvas,width=10,text='Save data',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,font=self.master.font,command=self.save_data)
        self.generate_report_button= tk.Button(self.canvas,width=13,text='Generate report',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,font=self.master.font,command=self.generate_report)

        self.video_time = EntryWithSet(self.canvas,width=10,text='',bg=self.master.color_hex,borderwidth=0,
                                       highlightthickness=0,font=self.master.font)



        # self.rectangle_width_entry = EntryWithSet(self.canvas,width=10,text='',bg=self.master.color_hex,borderwidth=0, highlightthickness=0,font=self.master.font)
        # self.rectangle_height_entry = EntryWithSet(self.canvas,width=10,text='',bg=self.master.color_hex,borderwidth=0, highlightthickness=0,font=self.master.font)
        # self.rectangle_width_entry.set('Width: 12')
        # self.rectangle_height_entry.set('Height: 12')
        # self.rectangle2_width_entry.configure(text='ej')
        # self.rectangle1_width_entry.pack(anchor=tk.NE)
        # self.rectangle2_width_entry.pack(anchor=tk.SE)

        # self.rectangle1_width_entry.place(x=self.master.width*0.5,y=0)
        # self.rectangle2_width_entry.place(x=self.master.width*0.5,y=self.master.height*0.8)



        def callback_video_bar(event):
            self.master.video.set_frame(int((event.x/self.video_bar_w)*self.master.video.number_of_frames_))
            self.update(force=True)
            self.generate_progress_bar()



        def callback(event):
            self.clickevent=(event.x,event.y)

            #scale so that it's returned in percentage of display

            linear_map_width = self.video_canvas_w/self.master.video.width_
            linear_map_height = self.video_canvas_h / self.master.video.height_

            self.click_x = int(event.x / linear_map_width)
            self.click_y = int(event.y / linear_map_height)

            if platform =='win32':
                k = [8,12]
            if platform == 'darwin':
                k = [4,6]

            if self.master.current_key not in k: #control button (ctrl):
                self.rectangle1.set_clicks(self.click_x,self.click_y)
            else:
                pass



        def callback_release(event):
            self.releaseevent=(event.x,event.y)
            self.rectangle1.point1 = self.clickevent
            self.rectangle1.point2 = self.releaseevent
        #

        # self.master.bind("<Key>",key)
        # self.master.bind("<KeyRelease>",key_release)
        self.video_canvas.bind("<Button-1>",callback)
        self.video_canvas.bind("<ButtonRelease-1>",callback_release)

        self.video_bar.bind("<Button-1>",callback_video_bar)

        # self.delay = 0

        self.previous_frame = self.frame
        self.frame_Image = Image.fromarray(self.frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        #HERE I REMOVED OSKAR
        self.image_id = self.video_canvas.create_image(int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
                                                       int((self.canvas_h * self.size_of_video_relative_to_canvas) / 2),
                                                       image=self.frame)
        self.video_bar_image_id = self.video_bar.create_image(
            int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
            int(self.video_bar_h / 2),
            image = self.bar)
        self.generate_progress_bar()
        self._resize()

    def _pack(self):
        self.generate_report_button.pack(side='bottom')  # should do only once
        self.save_data_button.pack(side='bottom')  # should do only once
        # self.rectangle_width_entry.pack(anchor=tk.NE)
        # self.rectangle_height_entry.pack(anchor=tk.NE)
        # self.cross_correlation_estimation_entry.pack(anchor=tk.NE)
        self.video_time.pack(anchor=tk.NE)
        self.video_bar.pack(side='bottom')
        self.video_canvas.pack(anchor=tk.CENTER)
        self.canvas.pack(anchor=tk.N,expand=tk.YES)
        self.pack(anchor=tk.CENTER)

    def _unpack(self):
        # self.generate_report_button.pack(anchor=tk.SE)  # should do only once
        # self.save_data_button.pack_forget()
        # self.rectangle_width_entry.pack_forget()
        # self.rectangle_height_entry.pack_forget()
        # self.cross_correlation_estimation_entry.pack_forget()
        self.video_time.pack_forget()
        self.video_canvas.pack_forget()
        self.canvas.pack_forget()
        self.pack_forget()

    def _destroy(self):
        self.video_canvas.destroy()
        self.canvas.destroy()
        self.destroy()

    def generate_progress_bar(self,percentage=None):
        width = int(self.video_bar_w)
        height = int(self.canvas_h * self.video_bar_relative_to_canvas)
        bar_color = [91,91,91]
        bar_fill_color=[204,0,1]

        if percentage is not None:
            progress_percent=percentage
        else:
            progress_percent = (self.master.video.get_frame_number()) / (self.master.video.number_of_frames_)

        bar = np.zeros([height,width,3])

        bar[:,:,0] = bar_color[0]
        bar[:,:,1] = bar_color[1]
        bar[:,:,2] = bar_color[2]

        bar[:,:int(progress_percent*width),0] = bar_fill_color[0]
        bar[:,:int(progress_percent * width),1] = bar_fill_color[1]
        bar[:,:int(progress_percent * width),2] = bar_fill_color[2]

        bar = cv2.merge((bar[:,:,0],bar[:,:,1],bar[:,:,2]))

        bar = Image.fromarray(bar.astype(np.uint8))
        self.bar = ImageTk.PhotoImage(bar)
        self.video_bar_image_id = self.video_bar.create_image(int(self.video_canvas_w / 2),int(self.video_bar_h / 2),
                                                              image=self.bar)

    def canvas_size(self,width,height): #input canvas size, not video canvas
        target_width = width * self.size_of_video_relative_to_canvas
        target_height = height * self.size_of_video_relative_to_canvas

        if target_width / target_height > self.master.video.aspect_ratio_:  # för bred, använd höjden för att skala
            video_frame_w = int(target_height / self.master.video.aspect_ratio_)
            video_frame_h = int(target_height)
        else:
            video_frame_h = int(target_width * self.master.video.aspect_ratio_)
            video_frame_w = int(target_width)
        return video_frame_w,video_frame_h

    def _resize(self,event=None):

        self.canvas_w = int(self.master.width*self.size_of_frame_relative_to_screen)
        self.canvas_h = int(self.master.height*self.size_of_frame_relative_to_screen)

        self.plot_canvas_w = int(self.canvas_w*0.1)
        self.plot_canvas_h = int(self.canvas_h*0.1)
        self.video_canvas_w,self.video_canvas_h = self.canvas_size(self.canvas_w,self.canvas_h)

        self.video_canvas.configure(width=self.video_canvas_w,
                                    height=self.video_canvas_h)
        self.canvas.create_window(int((self.canvas_w) / 2),int((self.canvas_h) / 2),window=self.video_canvas)
        self.image_id = self.video_canvas.create_image(self.video_canvas_w/2,self.video_canvas_h/2,image=self.frame)

        self.video_bar_h = int(self.video_canvas_h * self.video_bar_relative_to_canvas)
        self.video_bar_w = self.video_canvas_w

        self.video_bar.configure(width=self.video_canvas_w,height=self.video_bar_h)

        self.canvas.create_window(int((self.canvas_w) / 2),int(self.canvas_h/2)+int(self.video_canvas_h / 2),window=self.video_bar)

        self.generate_progress_bar()






    def set_video(self,path):

        self.click_x=0
        self.click_y=0

        self.master.video = ColorVideo(path) # need 2 remove
        frame = self.master.video.get_frame()
        self.frame_Image = Image.fromarray(frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        self.image = None
        self.ctrl_and_mouse_click_flag = 0
        self.state = False
        self.video_bar_click_x_coordinate = None

        self.master.blur_vector = np.zeros([self.master.video.number_of_frames_])

        self.master.current_key = 0
        self.rectangle1 = Rectangle(isForward=True)
        self.rectangle1.point1 = self.clickevent
        self.rectangle1.point2 = self.releaseevent

        #self.rectangle2 = Rectangle(isForward=False)

        #self.cross_correlation = CrossCorrelation(self.master.video,self.rectangle1,self.rectangle2)

        self.video_bar_w = self.video_canvas_w
        self.video_bar_h = int(self.video_canvas_h * self.video_bar_relative_to_canvas)


        self.generate_progress_bar()

        #HERE I REMOVE OSKAR
        # self.image_id = self.video_canvas.create_image(int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
        #                                                int((self.canvas_h * self.size_of_video_relative_to_canvas) / 2),
        #                                                image=self.frame)

        self.video_bar_image_id = self.video_bar.create_image(
            int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
            int(self.video_bar_h / 2),
            image = self.bar)

        # self._resize()
        self.master.video.set_frame(0)
        self.master.video.pause = 1


        self.flow_vector = dict(
            zip(np.arange(0,self.master.video.number_of_frames_),[np.nan] * self.master.video.number_of_frames_))
        self.mask_vector = dict(
            zip(np.arange(0,self.master.video.number_of_frames_),[np.nan] * self.master.video.number_of_frames_))

        self.written_csvs = 0

    # def get_rectangle_width_and_height(self):
    #     try:
    #         s = self.rectangle_height_entry.get()
    #         h=[int(s) for s in s.split() if s.isdigit()][0]
    #         # self.rectangle_height_entry.set('Height: '+str(h))
    #         s = self.rectangle_width_entry.get()
    #         w=[int(s) for s in s.split() if s.isdigit()][0]
    #         # self.rectangle_width_entry.set('Width: ' + str(w))
    #         self.rectangle1.set_width_and_height(w,h)
    #         self.rectangle2.set_width_and_height(w,h)
    #
    #     except:
    #         pass

    def save_data(self):

        if platform == 'win32':
            file_name = self.master.video.path.split('\\')[-1][:-4]
        if platform == 'darwin':
            file_name = self.master.video.path.split('/')[-1][:-4]

        self.master.save_report_name = ''
        print(self.master.save_report_name)
        self.popup = Save_Data_Popup(self.master)
        self.master.wait_window(self.popup.top)
        print(self.master.save_report_name)


        try:



            pickle_save(self.flow_vector,os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___flow.pickle'))
            pickle_save(self.mask_vector,os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___mask.pickle'))
            # pd.DataFrame(self.flow_vector).to_csv(os.path.join(self.master.statistics_directory_path,file_name + 'flow.csv'))
            # pd.DataFrame(self.mask_vector).to_csv(os.path.join(self.master.statistics_directory_path,file_name + 'mask.csv'))

        except:
            tk.messagebox.showerror("Error","An unknown error has occured")




    def generate_report(self):



        file_name = ''

        if platform == 'win32':
            file_name = self.master.video.path.split('\\')[-1][:-4]
        if platform == 'darwin':
            file_name = self.master.video.path.split('/')[-1][:-4]


        _tmp = glob.glob(os.path.join(self.master.statistics_directory_path,file_name) + '___*___flow.pickle')

        if len(_tmp)>0:
            list_of_reports=[]
            for item in _tmp:
                #file_path = os.path.basename(item).split('___')[0]
                print(item)
                print(os.path.basename(item).split('___'))
                report_name = os.path.basename(item).split('___')[1]
                list_of_reports.append(report_name)


        self.master.chosen_report_to_generate=''

        self.popup = Choose_Report_Popup(self.master,list_of_reports)
        self.master.wait_window(self.popup.top)

        a = pickle_load(os.path.join(self.master.statistics_directory_path,file_name + '___' +self.master.chosen_report_to_generate + '___mask.pickle'))
        b = pickle_load(os.path.join(self.master.statistics_directory_path,file_name + '___' +self.master.chosen_report_to_generate + '___flow.pickle'))
        #
        # a=pickle_load(os.path.join(self.master.statistics_directory_path,file_name + 'mask.pickle'))
        # b=pickle_load(os.path.join(self.master.statistics_directory_path,file_name + 'flow.pickle'))


        # this is the average flow magnitude for the selected area, measured in pixels.
        magnificationCoefficient = 1.328903654e-06 * 1000  # *1000 to get it in mm


        up = np.array([[np.nan] * (len(b) - 1)])[0]
        down = np.array([[np.nan] * (len(b) - 1)])[0]
        both=np.array([[np.nan]*(len(b)-1)])[0]

        for i in range(len(b) - 1):
            if str(b[i]) != 'nan':
                temp = b[i][:,:,2].copy()
                temp_ang = b[i][:,:,0].copy()
                temp[temp_ang < 90] = 0
                temp = temp / 25.5
                temp = temp * magnificationCoefficient
                up[i] = np.sum(temp) / np.sum(a[i])

        for i in range(len(b) - 1):
            if str(b[i]) != 'nan':
                temp = b[i][:,:,2].copy()
                temp_ang = b[i][:,:,0].copy()
                temp[temp_ang > 90] = 0
                temp = temp / 25.5
                temp = temp * magnificationCoefficient
                down[i] = np.sum(temp) / np.sum(a[i])

        for i in range(len(b) - 1):
            if str(b[i]) != 'nan':
                temp = b[i][:,:,2].copy()
                temp_ang = b[i][:,:,0].copy()
                temp = temp / 25.5
                temp = temp * magnificationCoefficient
                both[i] = np.sum(temp) / np.sum(a[i])

        f,ax = plt.subplots(figsize=(10,5),dpi=300)

        flow_field_up = pd.DataFrame(up,columns=['flow']).set_index(pd.Series(up).index / 30).dropna().ewm(span=100).mean()
        plt.plot(flow_field_up,label='up')

        flow_field_down = pd.DataFrame(down,columns=['flow']).set_index(pd.Series(down).index / 30).dropna().ewm(span=100).mean()
        plt.plot(flow_field_down,label='down')

        plt.title('Flow field magnitude ')
        plt.ylabel('Magnitude (mm)')
        plt.xlabel('Seconds')
        plt.legend()
        f.savefig(os.path.join(self.master.report_directory_path,file_name+ '___' + self.master.chosen_report_to_generate + '___up_and_down_.png'),dpi=f.dpi,transparent=True,bbox_inches = 'tight')

        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        flow_field_both = pd.DataFrame(both,columns=['flow']).set_index(pd.Series(both).index / 30).dropna().ewm(span=100).mean()
        plt.plot(flow_field_both,label='omnidirectional')
        plt.title('Flow field magnitude ')
        plt.ylabel('Magnitude (mm)')
        plt.xlabel('Seconds')
        plt.legend()
        f.savefig(os.path.join(self.master.report_directory_path,file_name+ '___' + self.master.chosen_report_to_generate + '___omnidirectional_.png'),dpi=f.dpi,transparent=True,bbox_inches = 'tight')

        # file_name=''
        #
        # if platform == 'win32':
        #     file_name = self.master.video.path.split('\\')[-1][:-4]
        # if platform == 'darwin':
        #     file_name = self.master.video.path.split('/')[-1][:-4]
        #
        # if os.path.isfile(os.path.join(self.master.statistics_directory_path,file_name + 'distance_vector.csv')) and \
        #     os.path.isfile(os.path.join(self.master.statistics_directory_path,file_name + 'cross_correlation.csv')) and \
        #     os.path.isfile(os.path.join(self.master.statistics_directory_path,file_name + 'blur_vector.csv')):
        #
        #     self.cross_correlation.generate_report(os.path.join(self.master.statistics_directory_path,file_name))
        # else:
        #     tk.messagebox.showerror("Error","There is no saved data, save data first in order to create a report")
















    def process_flow_frame(self,frame):


        frame = frame
        # frame = cv2.bitwise_and(frame,frame,mask=self.master.video.mask)
        return cv2.cvtColor(frame,cv2.COLOR_HSV2BGR)*4

        #return cv2.merge((frame[...,2],frame[...,2],frame[...,2]))




    def update(self,force=False):

        self.frame_number = self.master.video.get_frame_number()


        # if self.frame_number % 5 == 0:
        #     self.get_rectangle_width_and_height()



        if self.frame_number%5==0:
            self.generate_progress_bar()
            self.video_time.set('Time: ' + str(int(self.frame_number / 30)) + 's')
            # self.video_bar.itemconfig(self.video_bar_image_id,image=self.bar)

        if self.master.video.pause == 0 or force==True:
            # print('update')

            current_frame,rolling_frame = self.master.video.get_frame(rolling_average=10,return_non_average=1)
            frame = self.process_flow_frame(rolling_frame)
            self.previous_frame = frame

            if frame is not None:
                # print(frame)

                frame = self.rectangle1.draw_rectangle_drag(frame)
                self.flow_vector[self.frame_number]=self.rectangle1.get_selected_data_for_flow(current_frame)
                self.mask_vector[self.frame_number] = self.rectangle1.get_selected_data_for_mask(self.master.video.mask)

                # frame = self.rectangle2.draw_rectangle(frame)
                #
                #
                # self.cross_correlation.set_cropped_frame_data(self.frame_number,
                #                                               self.rectangle1.get_selected_data(),
                #                                               self.rectangle2.get_selected_data())
                # self.cross_correlation.calculate_distance(self.frame_number)
                # print(self.cross_correlation.distance_vector[self.frame_number])

                # self.master.blur_vector[self.frame_number] = calculate_blur(frame)



                self.frame_Image = Image.fromarray(frame)
                self.frame_Image = self.frame_Image.resize((self.video_canvas_w,self.video_canvas_h),Image.Resampling.LANCZOS)


                self.frame = ImageTk.PhotoImage(self.frame_Image)


                self.video_canvas.itemconfig(self.image_id,image=self.frame)


        else:
            frame = self.process_flow_frame(self.previous_frame)
            frame = self.rectangle1.draw_rectangle_drag(frame)
            self.frame_Image = Image.fromarray(frame)
            # self.video_frame_w,self.video_frame_h = self.canvas_size(self.canvas_w,self.canvas_h)
            self.frame_Image = self.frame_Image.resize((self.video_canvas_w,self.video_canvas_h),Image.Resampling.LANCZOS)
            self.frame = ImageTk.PhotoImage(self.frame_Image)
            self.video_canvas.itemconfig(self.image_id,image=self.frame)

        if self.master.video.finished:
            #if self.written_csvs==0:

                #self.save_report_data_and_generate_report()


                #self.written_csvs=1

            self.generate_progress_bar(1.0)
            # self.video_bar.itemconfig(self.video_bar_image_id,image=self.bar)

            # self.generate_progress_bar()


class ParticipantList(tk.Frame):
    def __init__(self, master,path='/Users/oskarwilhelmsson/Dropbox/Capris/Data',**kwargs):
        super(ParticipantList,self).__init__()
        # a.configure(bg=self.master.color_hex)
        # self.path = path
        self.master = master
        self.path = path
        self.items = self.get_items_from_path(self.path)
        self.boolean_stabilized = self.check_which_items_are_stabilized()

        self.master.videos_to_stabilize = np.array(self.items)[np.invert(self.boolean_stabilized)]

        self.list_objects = dict()
        # self.master.repack_analyze_frame_command = False #stupid solution to make frame update when delete item



        # tk.Frame.__init__(self, parent)
        # c = tk.Canvas.__init__(self,master,**kwargs)
        # self.canvas = tk.Canvas(self.master,bg=self.master.color_hex)
        #
        self.text = tk.Text(self, wrap="none",width=int(self.master.width*0.04))
        self.vsb = tk.Scrollbar(orient="vertical", command=self.text.yview,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)
        self.text.configure(yscrollcommand=self.vsb.set,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)

        self.temp_thumbnail_size=[]

        # self.selected_item =
        self.master.selected_item = self.items[0]  # always set first item as selected when initializing
        # try:
        #
        # except:
        #     self.master.selected_item=None
        self._pack()
        self.update()
        #self._repack()

        # self.update()
        # self.update()


    def _pack(self):
        self.vsb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)
        #self.pack(side='right')
        self.pack(side='right',fill='y')
        #self.configure(width=100)
        #self.configure(height=self.master.height)

    def _unpack(self):
        self.vsb.pack_forget()
        self.text.pack_forget()
        self.pack_forget()
    def _destroy(self):
        self.vsb.destroy()
        self.text.destroy()
        self.destroy()

    def get_items_from_path(self,path):
        a =glob.glob(path+'/*.avi')
        a.extend(glob.glob(path + '/*.mp4'))

        try:
            for index,file_name in enumerate(a):
                os.rename(file_name,file_name.replace(',',''))
                a[index] = file_name.replace(',','')
        except:
            pass
        return a #needs to be updated if new formats are allowed

    def check_which_items_are_stabilized(self):

        stabilized_items = self.get_items_from_path(self.path.replace('RecordedVideos','StabilizedVideos'))
        items = self.get_items_from_path(self.path)

        if platform == 'win32':
            a = [item.split('\\')[-1].split('.')[-2] for item in items]
            b = [item.split('\\')[-1].split('.')[-2] for item in stabilized_items]
        if platform == 'darwin':
            a = [item.split('/')[-1].split('.')[-2] for item in items]
            b = [item.split('/')[-1].split('.')[-2] for item in stabilized_items]
        print('windows mac:')
        print(a)

        return np.in1d(a,b) #in both lists

    def options_cmd(self,url):
        self.popup = Popup_Frame(self.master,url=url)
        self.master.wait_window(self.popup.top)

    def delete_video(self,url):

        os.remove(url)
        copy_dict = dict(self.list_objects)
        for k in copy_dict:
            self.list_objects[k].pack_forget()
            self.list_objects[k].destroy()
            del self.list_objects[k]

        self.text.pack_forget()
        self.text.pack(fill="both",expand=True)

        self.update()
    def _repack(self):
        copy_dict = dict(self.list_objects)

        for k in copy_dict:
            self.list_objects[k].pack_forget()
            self.list_objects[k].destroy()
            del self.list_objects[k]

        self.text.pack_forget()
        self.text.pack(fill="both",expand=True)

        self.update()


    def open_url(self,url):
        self.master.selected_item=url
        self._repack()
        #do stuff to the selected element

    def update(self):
        # self._unpack()
        # self._pack()


        self.list_objects = dict()

        self.items = self.get_items_from_path(self.path)

        self.text.delete('1.0',"end")
        try:
            self.text.delete('1.0',"end")
            # self.items = self.get_items_from_path(self.path)
            self.list_objects = dict()
        except:
            pass

        i = 0
        for index,item in enumerate(self.items):

            if self.boolean_stabilized[index]:
                self.items[index]=self.items[index].replace('RecordedVideos','StabilizedVideos')
                item =self.items[index]
            i+=1

            photo=None
            url=None
            b=None

            try:
                temp = ColorVideo(item)
            except:
                temp = Video(item)

            temp.generate_thumbnail()
            thumbnail = temp.thumbnail_
            self.temp_thumbnail_size = thumbnail.shape

            photo = ImageTk.PhotoImage(Image.fromarray(thumbnail))
            try:
                duration_in_seconds = int(temp.number_of_frames_ * (1 / temp.fps_))
            except:
                duration_in_seconds = 0
            seperator = '\n'

            if platform == 'win32':
                text_to_place = seperator.join([item.split('\\')[-1],'Length: ' + str(duration_in_seconds) + ' seconds'])
            if platform == 'darwin':
                text_to_place = seperator.join([item.split('/')[-1],'Length: ' + str(duration_in_seconds) + ' seconds'])


            b = tk.Label(self,image=photo,text=text_to_place,font=("Helvetica",10),anchor=tk.NW,compound=tk.LEFT,
                         justify=tk.LEFT,pady=5,bg=self.master.color_hex)
            b.pack(anchor=tk.N)



            if item == self.master.selected_item:
                b.config(relief='groove',borderwidth=2)

            if not self.boolean_stabilized[index]:
                b.config(bg='#BD766E') #red
                ## b.config(bg='#5C816B')  # green


            # else:
            #     photo = ImageTk.PhotoImage(Image.fromarray(thumbnail))
            #     try:
            #         duration_in_seconds = int(temp.number_of_frames_ * (1 / temp.fps_))
            #     except:
            #         duration_in_seconds = 0
            #     seperator = '\n'
            #     text_to_place = seperator.join([item.split('/')[-1],'Length: ' + str(duration_in_seconds)+' seconds'])
            #
            #     b = tk.Label(self,image=photo,text=text_to_place,font=("Helvetica",10),anchor=tk.NW,compound=tk.LEFT, justify=tk.LEFT,pady=5,bg=self.master.color_hex)
            #     b.pack(anchor=tk.N)


            b.image = photo  # keep a reference
            url = item  # change this to the name of the video
            b.bind("<Button-1>",lambda e,url=url: self.open_url(url))
            b.bind("<Button-2>",lambda e,url=url: self.options_cmd(url)) #self.delete_video(url)
            #b.bind("<Button-2>",lambda e,url=url: self.delete_video(url))
            self.text.window_create(str(index+1)+'.0',window=b)
            self.text.insert("end","\n")
            self.list_objects[item] = b

        self.text.configure(state="disabled")





#make canvas transparent:
#https://stackoverflow.com/questions/53021603/how-to-make-a-tkinter-canvas-background-transparent

#make canvas clickable:
#https://stackoverflow.com/questions/29211794/how-to-bind-a-click-event-to-a-canvas-in-tkinter
#https://stackoverflow.com/questions/29211794/how-to-bind-a-click-event-to-a-canvas-in-tkinter

