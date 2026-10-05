"""Tkinter widgets that make up the tabs: menu, video panels, video list, camera controls."""
import datetime
import glob
import logging
import os
import pickle
import tkinter as tk
from tkinter import messagebox

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image,ImageTk

from Caper import Video,ColorVideo,Rectangle,CrossCorrelation,VideoCamera
from Utilities import pickle_save,pickle_load,calculate_blur,list_videos,video_stem
from Popup_Frame import Popup_Frame
from Save_Data_Popup import Save_Data_Popup
from Choose_Report_Popup import Choose_Report_Popup


class EntryWithSet(tk.Entry):
    """
    A subclass to Entry that has a set method for setting its text to
    a given string, much like a Variable class.
    """

    def __init__(self, master, *args, **kwargs):
        tk.Entry.__init__(self, master, *args, **kwargs)

    def set(self, text_string):
        """
        Sets the object's text to text_string.
        """

        self.delete('0', 'end')
        self.insert('0', text_string)


def load_icon(path,size,color_rgb):
    """Image scaled to size x size, its transparency flattened onto the window colour."""
    temp_img = Image.open(path)
    temp_img = temp_img.resize((int(size),int(size)),Image.Resampling.LANCZOS)
    blank_image = Image.new('RGBA',(size,size),color_rgb)
    blank_image.paste(temp_img,mask=temp_img)
    r,g,b,a = cv2.split(np.array(blank_image))
    return ImageTk.PhotoImage(Image.fromarray(cv2.merge((r,g,b))))


def canvas_to_video_coordinates(canvas_x,canvas_y,canvas_w,canvas_h,video_w,video_h):
    """Map a click on the (scaled) video canvas back to a pixel in the video.

    The canvas shows the frame resized to canvas_w x canvas_h, so a canvas
    coordinate has to be divided by that scale factor before it can index the
    frame. Kept as a plain function so it can be checked without a display.
    """
    scale_x = float(canvas_w) / float(video_w)
    scale_y = float(canvas_h) / float(video_h)
    return int(canvas_x / scale_x),int(canvas_y / scale_y)


class CameraFrameSettings(tk.Frame):
    """Record button, FPS readout and recording timer on the Capture tab."""
    def __init__(self,master,*args,**kwargs):
        super(CameraFrameSettings,self).__init__()
        self.master = master
        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()
        self.height =int(self.screen_width*1.0)
        self.width= int(self.screen_height * 0.1)

        self.size_of_icon = int(self.width*0.4)

        self.image_path = 'Source/NotRecording.png'

        self.recording_timestamp=None

        self.canvas = tk.Canvas(self.master,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)
        self.generate_recording_button()
        self.generate_textbutton()
        self.generate_recording_length_textbutton()

        self.canvas.bind("<Configure>",self._resize)

    def _resize(self,event):
        self.button.place_forget()
        self.label.place_forget()
        self.fps_label.place_forget()

        self.screen_width= event.width
        self.screen_height = event.height

        self.height = int(self.screen_width * 1.0)
        self.width = int(self.screen_height * 0.2)
        self.size_of_icon = int(self.height * 0.4)
        self.button.place(x=self.width/20,y=self.height/2+10)
        self.label.place(x=self.width / 20,y=self.height / 2 + 50)

        self.fps_label.place(x=self.width/20,y=self.height/2-10)

        self.recording_length_label.place(x=self.width / 20,y=self.height / 2 + 85)

    def toggle(self):
        if self.master.record:
            self.image_path = 'Source/NotRecording.png'
            self.recording_timestamp=None
            self.recording_length_label.place_forget()
            self.master.video.destroy_writer()
            self.master.record = False
        else:
            self.image_path = 'Source/Recording.png'
            self.recording_timestamp = datetime.datetime.now()
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

    def update_recording_length_textbutton(self):
        if self.recording_timestamp is not None:
            t = str((datetime.datetime.now() - self.recording_timestamp).seconds)
            self.recording_length_label.config(text='Time: ' + t)

    def _unpack(self):
        self.canvas.pack_forget()
    def _pack(self):
        self.canvas.pack(side='right')

    def generate_recording_button(self):
        self.icon = load_icon(self.image_path,self.size_of_icon,self.master.color_rgb)
        self.button = tk.Button(self.canvas,width=self.size_of_icon,height=self.size_of_icon,bg=self.master.color_hex,image=self.icon,borderwidth=0,command=self.toggle)
        self.label = tk.Label(self.canvas,bg=self.master.color_hex,text='Record',font=self.master.font)

        self.button.place(x=self.width/20,y=self.height/2+10)
        self.label.place(x=self.width/20,y=self.height/2+50)

class Menu(tk.Frame):
    """Tab bar on the left: Capture, Analyze and Flow."""
    def __init__(self,master,*args,**kwargs):
        super(Menu,self).__init__()
        self.master = master
        self.screen_width = self.master.width
        self.screen_height = self.master.height
        self.width =int(self.screen_width*0.07)
        self.height = int(self.screen_height * 1.0)
        self.size_of_logos = int(self.width*0.9)

        self.master.selected_tab = 'analyze'

        self.canvas = tk.Canvas(self.master,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)

        self.logotype = load_icon('Source/Capture-Logo.png',self.size_of_logos,self.master.color_rgb)
        self.logotype_label = tk.Label(self.canvas,bg=self.master.color_hex,image=self.logotype)

        self.icon_capture = load_icon('Source/Capture3.png',self.size_of_logos,self.master.color_rgb)
        self.icon_analyze = load_icon('Source/Analyze.png',self.size_of_logos,self.master.color_rgb)
        self.icon_flow = load_icon('Source/Stabilize.png',self.size_of_logos,self.master.color_rgb)

        self.capture_button=tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Capture',image=self.icon_capture,borderwidth=0, highlightthickness=0,command=self.callback_capture)
        self.analyze_button = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Analyze',image=self.icon_analyze,borderwidth=0,highlightthickness=0,command=self.callback_analyze)
        self.flow_button = tk.Button(self.canvas,width=self.size_of_logos,height=self.size_of_logos,text='Flow',image=self.icon_flow,borderwidth=0,highlightthickness=0,command=self.callback_flow)

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
        self.flow_label = tk.Label(self.canvas,text='Flow',font=self.master.font,bg=self.master.color_hex)
        self.flow_button.place(x=offset_width,y=original_height+(offset_icon*2)+(offset_text*2))
        self.flow_label.place(x=offset_width+11,y=original_height + (offset_icon * 2)+(offset_text*3))

    def _pack(self):
        self.canvas.pack(side='left')

    def _unpack(self):
        self.canvas.pack_forget()

    def _destroy(self):
        self.canvas.destroy()

    def callback_capture(self):
        self.master.selected_tab = 'capture'
    def callback_analyze(self):
        self.master.selected_tab = 'analyze'
    def callback_flow(self):
        self.master.selected_tab = 'flow'


class VideoFrame(tk.Frame):
    """Analyze tab video panel: playback, the two ROI boxes, saving data and reports.

    Click places rectangle 1 (white), Ctrl+click places rectangle 2 (black).
    """
    def __init__(self,master,path,*args,**kwargs):
        super(VideoFrame, self).__init__()
        self.master = master

        self.size_of_frame_relative_to_screen = 0.7
        self.size_of_video_relative_to_canvas = 1.0

        self.canvas_w = int(self.master.width*self.size_of_frame_relative_to_screen)
        self.canvas_h = int(self.master.height*self.size_of_frame_relative_to_screen)
        self.video_canvas_w = self.canvas_w*self.size_of_video_relative_to_canvas
        self.video_canvas_h = self.canvas_h* self.size_of_video_relative_to_canvas

        self.video_bar_relative_to_canvas = 0.02

        self.click_x=0
        self.click_y=0

        self.registered_time_points = []

        self.canvas = tk.Canvas(self.master,width=self.canvas_w,height=self.canvas_h,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)
        self.video_canvas= tk.Canvas(self.canvas,width=self.video_canvas_w ,height=self.video_canvas_h,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)

        self.video_bar_w=self.video_canvas_w
        self.video_bar_h=int(self.video_canvas_h*self.video_bar_relative_to_canvas)
        self.video_bar = tk.Canvas(self.canvas,width=self.video_canvas_w,height=int(self.video_canvas_h * self.video_bar_relative_to_canvas),borderwidth=0,highlightthickness=0)

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

        def callback_video_bar(event):
            self.master.video.set_frame(int((event.x/self.video_bar_w)*self.master.video.number_of_frames_))
            self.update(force=True)
            self.generate_progress_bar()

        def callback(event):
            self.click_x,self.click_y = canvas_to_video_coordinates(event.x,event.y,
                                                                    self.video_canvas_w,self.video_canvas_h,
                                                                    self.master.video.width_,self.master.video.height_)

            # Read the Ctrl modifier straight off the mouse event. Bit 0x0004 is
            # the Control mask on both X11 (Linux/WSLg) and Windows. The old code
            # relied on a separately-tracked key state (current_key) that never
            # became "Control" under X11, so Ctrl+click always fell through to
            # rectangle1 and box 2 could not be placed.
            control_held = bool(event.state & 0x0004)
            if control_held: #control button (ctrl):
                self.rectangle2.set_clicks(self.click_x,self.click_y)
            else:
                self.rectangle1.set_clicks(self.click_x,self.click_y)

        self.video_canvas.bind("<Button-1>",callback)
        self.video_bar.bind("<Button-1>",callback_video_bar)

        self.previous_frame = self.frame
        self.frame_Image = Image.fromarray(self.frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        self.image_id = self.video_canvas.create_image(int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
                                                       int((self.canvas_h * self.size_of_video_relative_to_canvas) / 2),
                                                       image=self.frame)
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
                time_point_percent =(time_point*self.master.video.fps_) / (self.master.video.number_of_frames_)

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

        if target_width / target_height > self.master.video.aspect_ratio_:  # too wide: scale by the height
            video_frame_w = int(target_height / self.master.video.aspect_ratio_)
            video_frame_h = int(target_height)
        else:
            video_frame_h = int(target_width * self.master.video.aspect_ratio_)
            video_frame_w = int(target_width)
        return video_frame_w,video_frame_h

    def _resize(self,event=None):

        self.canvas_w = int(self.master.width*self.size_of_frame_relative_to_screen)
        self.canvas_h = int(self.master.height*self.size_of_frame_relative_to_screen)

        self.video_canvas_w,self.video_canvas_h = self.canvas_size(self.canvas_w,self.canvas_h)

        self.video_canvas.configure(width=self.video_canvas_w,height=self.video_canvas_h)
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

        self.master.video = Video(path)
        frame = self.master.video.get_frame()
        self.frame_Image = Image.fromarray(frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        try:
            self.registered_time_points = list(pd.read_csv(path.replace('StabilizedVideos','Statistics').replace('RecordedVideos','Statistics')[:-4]+'_registered_time_points.csv')['0'].values)
        except (FileNotFoundError,KeyError):
            self.registered_time_points=[]

        self.master.blur_vector = np.zeros([self.master.video.number_of_frames_])

        self.rectangle1 = Rectangle(isForward=True)
        self.rectangle2 = Rectangle(isForward=False)

        self.cross_correlation = CrossCorrelation(self.master.video,self.rectangle1,self.rectangle2,
                                                  mm_per_pixel=getattr(self.master,'mm_per_pixel',0.001328903654))

        self.video_bar_w = self.video_canvas_w
        self.video_bar_h = int(self.video_canvas_h * self.video_bar_relative_to_canvas)

        self.generate_progress_bar()

        self.video_bar_image_id = self.video_bar.create_image(
            int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
            int(self.video_bar_h / 2),
            image = self.bar)

        self.master.video.set_frame(0)
        # Start playing as soon as a video is loaded. This used to be set to 1
        # (paused), so a freshly loaded video sat frozen on frame 0 and looked
        # broken. Press P / Space to pause when you want to position the ROI
        # boxes on a still frame.
        self.master.video.pause = 0

    def get_rectangle_width_and_height(self):
        try:
            s = self.rectangle_height_entry.get()
            h=[int(s) for s in s.split() if s.isdigit()][0]
            s = self.rectangle_width_entry.get()
            w=[int(s) for s in s.split() if s.isdigit()][0]
            self.rectangle1.set_width_and_height(w,h)
            self.rectangle2.set_width_and_height(w,h)

        except (ValueError,IndexError):
            pass #entry does not contain a number (yet)

    def save_data(self):

        if self.cross_correlation.check_if_enough_data_for_report():

            self.master.save_report_name = ''
            self.popup = Save_Data_Popup(self.master)
            self.master.wait_window(self.popup.top)

            file_name = video_stem(self.master.video.path)

            pd.DataFrame(self.cross_correlation.get_mean_intensity()).to_csv(
                os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___cross_correlation.csv'))
            pd.DataFrame(self.master.blur_vector).to_csv(
                os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___blur_vector.csv'))
            pd.DataFrame(self.cross_correlation.distance_vector).to_csv(
                os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___distance_vector.csv'))
            pd.DataFrame(self.registered_time_points).to_csv(
                os.path.join(self.master.statistics_directory_path,file_name+'_registered_time_points.csv'))

        else:
            messagebox.showerror("Error", "Not enough data to save yet")

    def register_time_point(self):
        self.registered_time_points.append(self.frame_number/self.master.video.fps_)

    def generate_report(self):

        file_name = video_stem(self.master.video.path)

        a = glob.glob(os.path.join(self.master.statistics_directory_path,file_name) + '___*___cross_correlation.csv')

        if len(a)>0:
            list_of_reports=[]
            for item in a:
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
                messagebox.showerror("Error","There is no saved data, save data first in order to create a report")
        else:
            messagebox.showerror("Error","There are no saved reports")

    def update(self,force=False):
        self.frame_number = self.master.video.get_frame_number()

        if self.frame_number % 5 == 0:
            self.get_rectangle_width_and_height()
            self.video_time.set('Time: ' + str(int(self.frame_number / self.master.video.fps_))+'s')

        if self.frame_number % 20 == 0:
            cross_correlation_estimation=self.cross_correlation.estimate_cross_correlation(self.frame_number)
            self.cross_correlation_estimation_entry.set('Correlation: ' + cross_correlation_estimation)

        if self.frame_number%5==0:
            self.generate_progress_bar()

        if self.master.video.pause == 0 or force==True:
            frame = self.master.video.get_frame()
            self.previous_frame = frame

            if frame is not None:
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
            frame_Image = frame_Image.resize((self.video_canvas_w,self.video_canvas_h),Image.Resampling.LANCZOS)
            self.frame = ImageTk.PhotoImage(frame_Image)
            self.video_canvas.itemconfig(self.image_id,image=self.frame)

        if self.master.video.finished:
            self.generate_progress_bar(1.0)


class FlowFrame(tk.Frame):
    """Flow tab video panel: plays a flow video and records one drag-selected region."""
    def _canvas_to_video(self,canvas_x,canvas_y):
        return canvas_to_video_coordinates(canvas_x,canvas_y,
                                           self.video_canvas_w,self.video_canvas_h,
                                           self.master.video.width_,self.master.video.height_)

    def __init__(self,master,path,*args,**kwargs):
        super(FlowFrame, self).__init__()
        self.master = master

        self.size_of_frame_relative_to_screen = 0.7
        self.size_of_video_relative_to_canvas = 1.0

        self.canvas_w = int(self.master.width*self.size_of_frame_relative_to_screen)
        self.canvas_h = int(self.master.height*self.size_of_frame_relative_to_screen)
        self.video_canvas_w = self.canvas_w*self.size_of_video_relative_to_canvas
        self.video_canvas_h = self.canvas_h* self.size_of_video_relative_to_canvas

        self.video_bar_relative_to_canvas = 0.02

        self.click_x=0
        self.click_y=0
        self.clickevent = (0,0)
        self.releaseevent = (10,10)

        self.canvas = tk.Canvas(self.master,width=self.canvas_w,height=self.canvas_h,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)
        self.video_canvas= tk.Canvas(self.canvas,width=self.video_canvas_w ,height=self.video_canvas_h,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)

        self.video_bar_w=self.video_canvas_w
        self.video_bar_h=int(self.video_canvas_h*self.video_bar_relative_to_canvas)
        self.video_bar = tk.Canvas(self.canvas,width=self.video_canvas_w,height=int(self.video_canvas_h * self.video_bar_relative_to_canvas),borderwidth=0,highlightthickness=0)

        self.set_video(path)
        self.frame = self.master.video.get_frame()
        self.master.video.set_frame(0)

        self.save_data_button = tk.Button(self.canvas,width=10,text='Save data',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,font=self.master.font,command=self.save_data)
        self.generate_report_button= tk.Button(self.canvas,width=13,text='Generate report',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,font=self.master.font,command=self.generate_report)

        self.video_time = EntryWithSet(self.canvas,width=10,text='',bg=self.master.color_hex,borderwidth=0,
                                       highlightthickness=0,font=self.master.font)

        def callback_video_bar(event):
            self.master.video.set_frame(int((event.x/self.video_bar_w)*self.master.video.number_of_frames_))
            self.update(force=True)
            self.generate_progress_bar()

        # The Flow tab selects its region by click-and-drag. Both endpoints
        # must be in *video* pixel coordinates, because Rectangle clamps and
        # slices against the frame. The release handler used to store the raw
        # canvas coordinates while the press handler scaled to video
        # coordinates, so the box was drawn and sampled at the wrong place
        # whenever the canvas was not exactly the video's size (it never is:
        # the canvas is 70% of the window, aspect-fitted). The old Ctrl check
        # here was dead code — this tab has only one rectangle.
        def callback(event):
            self.click_x,self.click_y = self._canvas_to_video(event.x,event.y)
            self.clickevent = (self.click_x,self.click_y)
            self.rectangle1.set_clicks(self.click_x,self.click_y)

        def callback_release(event):
            self.releaseevent = self._canvas_to_video(event.x,event.y)
            self.rectangle1.point1 = self.clickevent
            self.rectangle1.point2 = self.releaseevent

        self.video_canvas.bind("<Button-1>",callback)
        self.video_canvas.bind("<ButtonRelease-1>",callback_release)

        self.video_bar.bind("<Button-1>",callback_video_bar)

        self.previous_frame = self.frame
        self.frame_Image = Image.fromarray(self.frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

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
        self.video_time.pack(anchor=tk.NE)
        self.video_bar.pack(side='bottom')
        self.video_canvas.pack(anchor=tk.CENTER)
        self.canvas.pack(anchor=tk.N,expand=tk.YES)
        self.pack(anchor=tk.CENTER)

    def _unpack(self):
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

        if target_width / target_height > self.master.video.aspect_ratio_:  # too wide: scale by the height
            video_frame_w = int(target_height / self.master.video.aspect_ratio_)
            video_frame_h = int(target_height)
        else:
            video_frame_h = int(target_width * self.master.video.aspect_ratio_)
            video_frame_w = int(target_width)
        return video_frame_w,video_frame_h

    def _resize(self,event=None):

        self.canvas_w = int(self.master.width*self.size_of_frame_relative_to_screen)
        self.canvas_h = int(self.master.height*self.size_of_frame_relative_to_screen)

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

        self.master.video = ColorVideo(path)
        frame = self.master.video.get_frame()
        self.frame_Image = Image.fromarray(frame)
        self.frame = ImageTk.PhotoImage(self.frame_Image)

        self.rectangle1 = Rectangle(isForward=True)
        self.rectangle1.point1 = self.clickevent
        self.rectangle1.point2 = self.releaseevent

        self.video_bar_w = self.video_canvas_w
        self.video_bar_h = int(self.video_canvas_h * self.video_bar_relative_to_canvas)

        self.generate_progress_bar()

        self.video_bar_image_id = self.video_bar.create_image(
            int((self.canvas_w * self.size_of_video_relative_to_canvas) / 2),
            int(self.video_bar_h / 2),
            image = self.bar)

        self.master.video.set_frame(0)
        self.master.video.pause = 1

        self.flow_vector = dict(
            zip(np.arange(0,self.master.video.number_of_frames_),[np.nan] * self.master.video.number_of_frames_))
        self.mask_vector = dict(
            zip(np.arange(0,self.master.video.number_of_frames_),[np.nan] * self.master.video.number_of_frames_))

    def save_data(self):

        file_name = video_stem(self.master.video.path)

        self.master.save_report_name = ''
        self.popup = Save_Data_Popup(self.master)
        self.master.wait_window(self.popup.top)

        try:
            pickle_save(self.flow_vector,os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___flow.pickle'))
            pickle_save(self.mask_vector,os.path.join(self.master.statistics_directory_path,file_name + '___' + self.master.save_report_name + '___mask.pickle'))

        except Exception:
            logging.exception('Saving flow data failed')
            messagebox.showerror("Error","Saving flow data failed, see capillaroscopy.log")

    def generate_report(self):

        file_name = video_stem(self.master.video.path)

        _tmp = glob.glob(os.path.join(self.master.statistics_directory_path,file_name) + '___*___flow.pickle')

        if len(_tmp)>0:
            list_of_reports=[]
            for item in _tmp:
                report_name = os.path.basename(item).split('___')[1]
                list_of_reports.append(report_name)

        self.master.chosen_report_to_generate=''

        self.popup = Choose_Report_Popup(self.master,list_of_reports)
        self.master.wait_window(self.popup.top)

        a = pickle_load(os.path.join(self.master.statistics_directory_path,file_name + '___' +self.master.chosen_report_to_generate + '___mask.pickle'))
        b = pickle_load(os.path.join(self.master.statistics_directory_path,file_name + '___' +self.master.chosen_report_to_generate + '___flow.pickle'))

        # this is the average flow magnitude for the selected area, measured in pixels.
        magnificationCoefficient = getattr(self.master,'mm_per_pixel',0.001328903654) # spatial calibration, configured in settings.csv
        fps = self.master.video.fps_ or 30

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

        flow_field_up = pd.DataFrame(up,columns=['flow']).set_index(pd.Series(up).index / fps).dropna().ewm(span=100).mean()
        plt.plot(flow_field_up,label='up')

        flow_field_down = pd.DataFrame(down,columns=['flow']).set_index(pd.Series(down).index / fps).dropna().ewm(span=100).mean()
        plt.plot(flow_field_down,label='down')

        plt.title('Flow field magnitude ')
        plt.ylabel('Magnitude (mm)')
        plt.xlabel('Seconds')
        plt.legend()
        f.savefig(os.path.join(self.master.report_directory_path,file_name+ '___' + self.master.chosen_report_to_generate + '___up_and_down_.png'),dpi=f.dpi,transparent=True,bbox_inches = 'tight')

        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        flow_field_both = pd.DataFrame(both,columns=['flow']).set_index(pd.Series(both).index / fps).dropna().ewm(span=100).mean()
        plt.plot(flow_field_both,label='omnidirectional')
        plt.title('Flow field magnitude ')
        plt.ylabel('Magnitude (mm)')
        plt.xlabel('Seconds')
        plt.legend()
        f.savefig(os.path.join(self.master.report_directory_path,file_name+ '___' + self.master.chosen_report_to_generate + '___omnidirectional_.png'),dpi=f.dpi,transparent=True,bbox_inches = 'tight')

    def process_flow_frame(self,frame):
        return cv2.cvtColor(frame,cv2.COLOR_HSV2BGR)*4

    def update(self,force=False):

        self.frame_number = self.master.video.get_frame_number()

        if self.frame_number%5==0:
            self.generate_progress_bar()
            self.video_time.set('Time: ' + str(int(self.frame_number / self.master.video.fps_)) + 's')

        if self.master.video.pause == 0 or force==True:
            current_frame,rolling_frame = self.master.video.get_frame(rolling_average=10,return_non_average=1)
            # Keep the *unprocessed* frame: the paused branch below runs
            # process_flow_frame on previous_frame, and this used to store the
            # already-converted frame, so pausing (the state every flow video
            # loads in) showed an HSV->BGR conversion applied twice.
            self.previous_frame = rolling_frame
            frame = self.process_flow_frame(rolling_frame)

            if frame is not None:
                frame = self.rectangle1.draw_rectangle_drag(frame)
                self.flow_vector[self.frame_number]=self.rectangle1.get_selected_data_for_flow(current_frame)
                self.mask_vector[self.frame_number] = self.rectangle1.get_selected_data_for_mask(self.master.video.mask)

                self.frame_Image = Image.fromarray(frame)
                self.frame_Image = self.frame_Image.resize((self.video_canvas_w,self.video_canvas_h),Image.Resampling.LANCZOS)

                self.frame = ImageTk.PhotoImage(self.frame_Image)

                self.video_canvas.itemconfig(self.image_id,image=self.frame)

        else:
            frame = self.process_flow_frame(self.previous_frame)
            frame = self.rectangle1.draw_rectangle_drag(frame)
            self.frame_Image = Image.fromarray(frame)
            self.frame_Image = self.frame_Image.resize((self.video_canvas_w,self.video_canvas_h),Image.Resampling.LANCZOS)
            self.frame = ImageTk.PhotoImage(self.frame_Image)
            self.video_canvas.itemconfig(self.image_id,image=self.frame)

        if self.master.video.finished:
            self.generate_progress_bar(1.0)


class ParticipantList(tk.Frame):
    """Scrollable list of the videos in one folder, with thumbnails.

    Left click opens a video; Button-2 (middle click on Linux/Windows, right
    click on macOS) opens its options popup. Videos without a stabilized copy
    are shown in red.
    """
    def __init__(self,master,path):
        super(ParticipantList,self).__init__()
        self.master = master
        self.path = path
        self.items = list_videos(self.path)

        if len(self.items) == 0 and 'RecordedVideos' in self.path:
            stabilized_path = self.path.replace('RecordedVideos','StabilizedVideos')
            if len(list_videos(stabilized_path)) > 0:
                self.path = stabilized_path
                self.items = list_videos(self.path)

        self.boolean_stabilized = self.check_which_items_are_stabilized()

        self.list_objects = dict()

        self.text = tk.Text(self, wrap="none",width=int(self.master.width*0.04))
        self.vsb = tk.Scrollbar(orient="vertical", command=self.text.yview,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)
        self.text.configure(yscrollcommand=self.vsb.set,bg=self.master.color_hex,borderwidth=0, highlightthickness=0)

        if len(self.items) > 0:
            self.master.selected_item = self.items[0]  # always set first item as selected when initializing
        else:
            self.master.selected_item = None
        self._pack()
        self.update()

    def _pack(self):
        self.vsb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)
        self.pack(side='right',fill='y')

    def _unpack(self):
        self.vsb.pack_forget()
        self.text.pack_forget()
        self.pack_forget()
    def _destroy(self):
        self.vsb.destroy()
        self.text.destroy()
        self.destroy()

    def get_thumbnail_and_duration(self,item):
        #thumbnails are cached on disk so the list does not have to decode
        #every video again on each refresh
        cache_dir = os.path.join(os.path.dirname(item),'.thumbnails')
        cache_file = os.path.join(cache_dir,os.path.basename(item) + '.pickle')
        try:
            if os.path.getmtime(cache_file) >= os.path.getmtime(item):
                cached = pickle_load(cache_file)
                return cached['thumbnail'],cached['duration']
        except (OSError,KeyError,pickle.UnpicklingError,EOFError):
            pass #no usable cache entry, regenerate below

        try:
            temp = ColorVideo(item)
        except (FileNotFoundError,EOFError,pickle.UnpicklingError):
            #not a flow video (no sidecar pickle) - treat as a plain video
            temp = Video(item)

        temp.generate_thumbnail()
        thumbnail = temp.thumbnail_
        temp.cap.release()
        try:
            duration = int(temp.number_of_frames_ * (1 / temp.fps_))
        except ZeroDivisionError:
            duration = 0

        try:
            os.makedirs(cache_dir,exist_ok=True)
            pickle_save({'thumbnail': thumbnail,'duration': duration},cache_file)
        except OSError:
            logging.exception('Could not write thumbnail cache for %s',item)
        return thumbnail,duration

    def check_which_items_are_stabilized(self):
        stabilized_items = list_videos(self.path.replace('RecordedVideos','StabilizedVideos'))
        items = list_videos(self.path)
        a = [video_stem(item) for item in items]
        b = [video_stem(item) for item in stabilized_items]
        return np.isin(a,b) #in both lists

    def options_cmd(self,url):
        self.popup = Popup_Frame(self.master,url=url)
        self.master.wait_window(self.popup.top)

    def delete_video(self,url):
        os.remove(url)
        self._repack()

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

    def update(self):
        self.list_objects = dict()

        self.items = list_videos(self.path)

        self.text.delete('1.0',"end")

        for index,item in enumerate(self.items):

            if self.boolean_stabilized[index]:
                self.items[index]=self.items[index].replace('RecordedVideos','StabilizedVideos')
                item =self.items[index]

            thumbnail,duration_in_seconds = self.get_thumbnail_and_duration(item)

            photo = ImageTk.PhotoImage(Image.fromarray(thumbnail))
            text_to_place = '\n'.join([os.path.basename(item),'Length: ' + str(duration_in_seconds) + ' seconds'])

            b = tk.Label(self,image=photo,text=text_to_place,font=("Helvetica",10),anchor=tk.NW,compound=tk.LEFT,
                         justify=tk.LEFT,pady=5,bg=self.master.color_hex)
            b.pack(anchor=tk.N)

            if item == self.master.selected_item:
                b.config(relief='groove',borderwidth=2)

            if not self.boolean_stabilized[index]:
                b.config(bg='#BD766E') #red

            b.image = photo  # keep a reference
            url = item
            b.bind("<Button-1>",lambda e,url=url: self.open_url(url))
            b.bind("<Button-2>",lambda e,url=url: self.options_cmd(url))
            self.text.window_create(str(index+1)+'.0',window=b)
            self.text.insert("end","\n")
            self.list_objects[item] = b

        self.text.configure(state="disabled")
