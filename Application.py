
# import rumps
# rumps.debug_mode(True)
import sys
import logging
import traceback
if "Tkinter" not in sys.modules:
    import tkinter as tk
from tkinter import messagebox
import numpy as np
import pickle
from PIL import ImageTk,Image
import cv2
import time
from Caper import Video,Rectangle,CrossCorrelation
import datetime
from Utilities import *
from FrameClasses import VideoFrame,ParticipantList,MatplotlibFrame
import sys
from webcolors import rgb_to_hex
from tkinter import ttk as ttk
from FrameClasses import VideoFrame,Menu

from Analyze_Frame import Analyze_Frame
from Camera_Frame import Camera_Frame
from Stabilize_Frame import Stabilize_Frame
from Flow_Frame import Flow_Frame
from Process_Frame import Process_Frame

import time
import os
from sys import platform
from tkinter import filedialog
import pandas as pd

class Application(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        self.master = master

        # self.canvas = tk.Canvas(self.master)
        self.master.color_rgb = (230,230,230,0)
        self.master.color_hex = rgb_to_hex(self.master.color_rgb[:3])
        if platform == 'darwin' or platform == 'linux':
            self.master.font = ("Helvetica",14)
            self.master.height = 770
        else:
            self.master.font = ("Helvetica",12)
            self.master.height = 700

        self.delay = 1
        self.previously_selected_tab = 'analyze'
        self.selected_tab='analyze'

        self.master.width = 1150


        self.master.geometry("{}x{}".format(str(self.master.width),str(self.master.height)))


        self.mouse_released = False
        self.state = False
        self._reported_errors = set()
        self.master.options=None
        self.master.url=None
        self.master.stop=False

        self.master.master_canvas=tk.Frame(self.master,bg=self.master.color_hex,borderwidth=0, highlightthickness=0,width=100,height=10)
        self.master.master_canvas.pack(fill=tk.BOTH,expand=1)

        # settings.csv holds persistent configuration:
        #   Application_path - folder holding RecordedVideos/, StabilizedVideos/ etc.
        #   mm_per_pixel     - spatial calibration of the capillaroscope optics
        #                      (mm per image pixel), used to convert pixel velocities
        #                      to mm/s. The default was calibrated for the original
        #                      study microscope; recalibrate when the hardware changes.
        default_settings = {'mm_per_pixel': '0.001328903654'}
        try:
            df = pd.read_csv('settings.csv')
            self.master.settings = pd.DataFrame(df.to_numpy()[:,1],index=df.to_numpy()[:,0])
            self.master.program_directory = self.master.settings.loc['Application_path'].values[0]
        except Exception:
            # first time the program is opened: ask for a data folder
            logging.exception('Could not read settings.csv, creating a new one')
            self.master.program_directory = filedialog.askdirectory(initialdir='desktop',title='Select application folder')
            self.master.settings = pd.DataFrame([self.master.program_directory],index=['Application_path'])

        # fill in any missing settings with defaults and persist them
        settings_changed = not os.path.isfile('settings.csv')
        for key,value in default_settings.items():
            if key not in self.master.settings.index:
                self.master.settings.loc[key] = value
                settings_changed = True
        if settings_changed:
            self.master.settings.to_csv('settings.csv')

        self.master.mm_per_pixel = float(self.master.settings.loc['mm_per_pixel'].values[0])

        self.master.recorded_video_directory_path = os.path.join(self.master.program_directory,'RecordedVideos')
        self.master.stabilized_video_directory_path = os.path.join(self.master.program_directory,'StabilizedVideos')
        self.master.report_directory_path = os.path.join(self.master.program_directory,'Reports')
        self.master.statistics_directory_path = os.path.join(self.master.program_directory,'Statistics')
        self.master.flows_directory_path = os.path.join(self.master.program_directory,'Flows')
        for directory_path in (self.master.recorded_video_directory_path,
                               self.master.stabilized_video_directory_path,
                               self.master.report_directory_path,
                               self.master.statistics_directory_path,
                               self.master.flows_directory_path):
            os.makedirs(directory_path,exist_ok=True)






        self.menu = Menu(self.master)
        self.menu._pack()
        self.tab = Analyze_Frame(self.master)
        self.tab._pack()
        self.master.master_canvas.pack()

        self.master.bind("<ButtonRelease-1>",self.callback_release)
        self.master.bind("<Button-1>",self.callback_click)
        self.master.bind("<Key>",self.key_event)
        self.master.bind("<KeyRelease>",self.key_release)
        self.master.bind("<Escape>",self.quit_application)
        self.master.bind("<Configure>",self._resize)



        self.update()

        #handles clicking close button
        def on_closing():
            sys.exit()
        self.master.protocol('WM_DELETE_WINDOW',on_closing)
        self.master.mainloop()


    def key_event(self,event=None):
        # if event.char == 'f':
        #     self.toggle_fullscreen()


        self.master.current_key = event.state

        jump=5

        try:
            if event.char=='a' or event.char=='A' or event.char=='\uf702':
                self.tab.video_frame.rectangle1.move_clicks(-jump,0)
                self.tab.video_frame.rectangle2.move_clicks(-jump,0)
            if event.char=='w' or event.char=='W' or event.char=='\uf700':
                self.tab.video_frame.rectangle1.move_clicks(0,-jump)
                self.tab.video_frame.rectangle2.move_clicks(0,-jump)
            if event.char=='d' or event.char=='D' or event.char=='\uf703':
                self.tab.video_frame.rectangle1.move_clicks(jump,0)
                self.tab.video_frame.rectangle2.move_clicks(jump,0)
            if event.char=='s' or event.char=='S' or event.char=='\uf701':
                self.tab.video_frame.rectangle1.move_clicks(0,jump)
                self.tab.video_frame.rectangle2.move_clicks(0,jump)

            if event.char == 'q' or event.char == 'Q':
                self.master.video.go_back_or_forward_n_frames(-500)
            if event.char == 'e' or event.char == 'E':
                self.master.video.go_back_or_forward_n_frames(500)
            if event.char == 'p' or event.char == ' ':
                self.master.video.pause= 1-self.master.video.pause
        except AttributeError:
            pass #no video loaded yet, so there is nothing to control

    def key_release(self,event):
        self.master.current_key = None

    def toggle_fullscreen(self,event=None):
        self.state = not self.state  # Just toggling the boolean
        self.master.attributes("-fullscreen",self.state)
        if self.state is False:
        # #     # self.master.width = 1000
        # #     # self.master.height = 700
        # #     # self.master.configure(width=self.master.width,height=self.master.height)
            self.tab._resize()

    def quit_application(self,event=None):
        self.master.destroy()
        sys.exit()

    def callback_click(self,event=None):

        self.mouse_released = False

    def callback_release(self,event=None):
        self.mouse_released=True
        self.ctrl_and_mouse_click_flag = 0

    def _resize(self,event=None,force=False):
        # print(self.master.width,self.master.height)
        self.master.stop=True
        # Do NOT force video.pause here. <Configure> fires during normal window
        # setup and redraws, and this handler never set pause back to 0, so the
        # video froze on frame 0 and appeared to never play. The video canvas is
        # a fixed size, so there is nothing to protect by pausing on resize.
        if self.mouse_released:
            if event.width<300 or event.height<300:
                self.master.width = 1000
                self.master.height = 700

            else:
                if event is not None:
                    pass
                    # print(self.master.width,event.width)
                    # self.master.width = event.width
                    # self.master.height = event.height
                    # self.tab._resize()
                # self.master.master_canvas.configure(width=self.master.width,
                #                             height=self.master.height)

            self.mouse_released = False
        self.master.stop = False
        # print(self.master.width,self.master.height)

    def options_update(self):
        if self.master.options is not None:
            # self.selected_tab = 'processing'
            self.master.selected_tab = 'processing'
            # self.process = Processing(self.master,self.master.url,self.master.options)


            #
            # if self.master.options == 'delete':
            #
            #     try:
            #         self.tab.participant_list.delete_video(self.master.url)
            #     except:
            #         pass
            # if self.master.options == 'stabilize':
            #     print('stabilize')
            #
            # if self.master.options == 'stabilize_all':
            #     print('stabilize_all')
            # if self.master.options == 'flow':
            #     self.info = Display_Info_Frame(self.master,self.master.url)
            #     print('flow')
            #     self.info.text = 'flow'
            #     self.info.update('flow')
            # if self.master.options == 'flow_all':
            #     print('flow_all')

            # delete_video



    def fps_ticker(self):
        try:
            self.timestamp = datetime.datetime.now()
            self.master.fps = 1.0 / float((self.timestamp - self.previous_timestamp).microseconds / 1000000)
            self.previous_timestamp = self.timestamp

            if ((-1.0/self.master.fps))>(1.0/30.0):
                self.delay = int((1.0 / 30.0)-(-1.0 / self.master.fps)*1000) #measured in milliseconds

        except (AttributeError,ZeroDivisionError):
            #first tick has no previous timestamp yet
            self.previous_timestamp = datetime.datetime.now()
            self.master.fps = 30

    def update(self):
        # Any uncaught exception here would end the after() chain and freeze the
        # whole UI, so log it and keep the loop alive instead.
        try:
            self._update_body()
        except Exception:
            logging.exception('Unhandled error in main update loop')
            self._report_update_error(traceback.format_exc())
        self.master.after(self.delay,self.update)

    def _report_update_error(self,tb):
        error_key = tb.strip().splitlines()[-1]
        if error_key not in self._reported_errors:
            self._reported_errors.add(error_key)
            messagebox.showerror('Unexpected error',
                                 'The application hit an error but will keep running.\n\n'
                                 + error_key +
                                 '\n\nSee capillaroscopy.log for the full traceback.')

    def _update_body(self):
        self.options_update()
        # Pace the loop to the video's native frame rate so playback runs at real
        # speed. This was hard-coded to 1 ms, which ran videos at hundreds of fps
        # -- they flashed past in a fraction of a second and looked frozen.
        self.delay=1 #one millisecond, (can't be zero)
        if hasattr(self.master,'video') and self.master.video is not None:
            fps = getattr(self.master.video,'fps_',0) or 0
            if fps > 0:
                self.delay = max(1,int(round(1000.0/fps)))


        self.previously_selected_tab =self.selected_tab
        self.selected_tab = self.master.selected_tab

        self.fps_ticker()
        if self.selected_tab != self.previously_selected_tab:

            if self.selected_tab == 'capture':

                self.tab._unpack()
                self.tab._destroy()
                self.tab=Camera_Frame(self.master)
                self.tab._pack()
                self.selected_tab = 'capture'
                self.master.selected_tab = 'capture'

            if self.selected_tab == 'analyze':
                self.tab._unpack()
                self.tab._destroy()
                self.tab=Analyze_Frame(self.master)
                self.tab._pack()
                # self.tab._unpack()

                self.selected_tab = 'analyze'
                self.master.selected_tab = 'analyze'
                # self.previously_selected_tab = 'analyze'

            if self.selected_tab == 'stabilize':
                self.tab._unpack()
                self.tab._destroy()
                self.tab=Stabilize_Frame(self.master)
                self.tab._pack()
                # self.tab._unpack()

                self.selected_tab = 'stabilize'
                self.master.selected_tab = 'stabilize'
                # self.previously_selected_tab = 'analyze'

            if self.selected_tab == 'flow':
                self.tab._unpack()
                self.tab._destroy()
                self.tab=Flow_Frame(self.master)
                self.tab._pack()
                # self.tab._unpack()

                self.selected_tab = 'flow'
                self.master.selected_tab = 'flow'

            if self.selected_tab == 'processing':
                # self.tab._unpack()
                # self.tab._destroy()
                self.selected_tab = 'processing'
                self.master.selected_tab = 'processing'
                self.process_tab = Process_Frame(self.master,self.master.url,self.master.options,self.tab,self.previously_selected_tab)
                self.process_tab._pack()
                self.delay=1

        if self.selected_tab == 'processing':
            self.process_tab.update()

        self.tab.update()

        self.previously_selected_tab = self.selected_tab


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            logging.FileHandler('capillaroscopy.log'),
            logging.StreamHandler(),
        ],
    )

    root = tk.Tk()
    root.title("Capture")
    root.wm_title("Capture")
    # root.geometry("1000x700")
    # color_rgb = (230,230,230,0)
    # color_hex=rgb_to_hex(color_rgb[:3])
    # root["bg"] = color_hex

    # gui.mainloop()
    #
    #sp=os.getcwd()
    imgicon = tk.PhotoImage(file=os.path.join('Source','Capture-Logo.png'))
    root.tk.call('wm','iconphoto',root._w,imgicon)
    gui = Application(root)

