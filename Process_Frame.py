

import sys
if "Tkinter" not in sys.modules:
    import tkinter as tk
import numpy as np
import pickle
from PIL import ImageTk,Image
import cv2
import time
import datetime
from Utilities import *
import sys
from webcolors import rgb_to_hex
from tkinter import ttk as ttk
from Caper import Video,Rectangle,VideoCamera,VideoStabilization,VideoStabilizationMultiple,FlowVideo,FlowVideoMultiple
from sys import platform
import glob

class Process_Frame(tk.Frame):
    def __init__(self, master, url,command,tab,previously_selected_tab,*args, **kwargs):
        self.previously_selected_tab = previously_selected_tab
        #super(Popup_Frame,self).__init__()
        super().__init__()
        self.tab = tab
        self.master = master
        self.url = url
        self.command = command

        self.top= tk.Toplevel()
        # self.main_frame=self.master.master_canvas
        #self.frame = tk.Frame(self.top,width=300,height=100,bg=self.master.color_hex,
        #                        borderwidth=0,highlightthickness=0)

        self.width = 220
        self.height_of_button = 20
        self.height=self.height_of_button*7

        self.master.options=None
        self.master.url=url

        self.text = ''
        self.iteration = 0
        self.process=None
        self.items=None

        self.canvas = tk.Canvas(self.top,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0,highlightthickness=0)

        factor = 0.10

        self.top.wm_title('Processing ...')
        self.information_label = tk.Label(self.canvas,text=self.text,borderwidth=0,bg=self.master.color_hex)
        # self.btn1 = tk.Button(self.canvas, text='Delete',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd1)
        # self.btn2 = tk.Button(self.canvas, text='Stabilize',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd2)
        # self.btn3 = tk.Button(self.canvas,text='Stabilize all videos',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd3)
        # self.btn4 = tk.Button(self.canvas, text='Calculate flow',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd4)
        # self.btn5 = tk.Button(self.canvas,text='Calculate flow for all',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd5)

        self.window1= self.canvas.create_window(int((self.width/2)-4.5*((self.width*factor))),self.height_of_button,anchor=tk.NW,window=self.information_label)
        # self.window2 = self.canvas.create_window(int((self.width/2)-4.5*((self.width*factor))),self.height_of_button*2,anchor=tk.NW,window=self.btn2)
        # self.window3= self.canvas.create_window(int((self.width/2)-4.5*((self.width*factor))),self.height_of_button*3,anchor=tk.NW,window=self.btn3)
        # self.window4 = self.canvas.create_window(int((self.width / 2) - 4.5 * ((self.width *factor))),self.height_of_button * 4,anchor=tk.NW,window=self.btn4)
        # self.window5 = self.canvas.create_window(int((self.width / 2) - 4.5 * ((self.width*factor))),self.height_of_button * 5,anchor=tk.NW,window=self.btn5)


        x = self.master.winfo_x()
        y = self.master.winfo_y()
        w = self.width
        h = self.height
        dx=int(self.master.width*0.7)
        dy = int(self.master.height*0.2)
        self.top.geometry("%dx%d+%d+%d" % (w,h,x + dx,y + dy))


        self._pack()

        # print(self.command)
        if self.command=='delete':

            self.tab.participant_list.delete_video(self.url)


        if self.command=='stabilize':
            self.process = VideoStabilization(path=self.url)

        if self.command=='stabilize_all':
            self.master.videos_to_stabilize = self.check_which_items_are_stabilized()
            self.process = VideoStabilizationMultiple(paths=self.master.videos_to_stabilize)

        if self.command=='flow':

            if self.url.find('StabilizedVideos') != -1:
                self.process = FlowVideo(path=self.url)
            else:
                self.process = None
                tk.messagebox.showerror("Error","Video needs to be stabilized first")

        if self.command=='flow_all':
            stabilized_items = self.get_items_from_path(self.master.stabilized_video_directory_path)
            flow_items = self.get_items_from_path(self.master.flows_directory_path)

            if platform == 'win32':
                a = [item.split('\\')[-1].split('.')[-2] for item in stabilized_items]
                b = [item.split('\\')[-1].split('.')[-2] for item in flow_items]
            if platform == 'darwin' or platform == 'linux':
                a = [item.split('/')[-1].split('.')[-2] for item in stabilized_items]
                b = [item.split('/')[-1].split('.')[-2] for item in flow_items]

            items_to_flow_process = np.array(stabilized_items)[np.invert(np.in1d(a,b))]


            self.process = FlowVideoMultiple(paths=items_to_flow_process)

        self.top.protocol('WM_DELETE_WINDOW',self.on_closing)

    def _resize(self,event=None):
        pass


    def _unpack(self):
        # self.btn1.pack_forget()
        # self.btn2.pack_forget()
        # self.btn3.pack_forget()
        # self.btn1.place_forget()
        # self.btn2.place_forget()
        # self.btn3.place_forget()
        self.canvas.pack_forget()
        # self.frame.pack_forget()
        # self.matplotlib_frame._unpack()
        # self.main_frame.pack_forget()

    def _pack(self):
        # self.btn1.pack(anchor=tk.CENTER)
        # self.btn2.pack(anchor=tk.CENTER)
        # self.btn3.pack(anchor=tk.CENTER)
        # self.frame.pack()
        self.canvas.pack()
        # self.btn1.pack(side='top')
        # self.btn2.pack(side='top')
        # self.btn3.pack(side='top')
        # self.btn1.place(x=int(self.width/2-((self.width/30)/2)),y=self.height_of_button)
        # self.btn2.place(x=int(self.width/2-((self.width/30))),y=self.height_of_button*2)
        # self.btn3.place(x=150,y=self.height_of_button*3)

        # self.canvas.pack(fill=tk.BOTH,expand=1)
        # self.matplotlib_frame._pack()
        # self.main_frame.pack()

    def _destroy(self):
        # self.btn1.destroy()
        # self.btn2.destroy()
        # self.btn3.destroy()
        self.canvas.destroy()

    #handles clicking close button
    def on_closing(self):
        self.process = None
        # self._unpack()
        # self._destroy()
        # self.top.destroy()



    def set_text(self,t):
        self.t = t




    def check_which_items_are_stabilized(self):

        stabilized_items = self.get_items_from_path(self.master.recorded_video_directory_path.replace('RecordedVideos','StabilizedVideos'))
        items = self.get_items_from_path(self.master.recorded_video_directory_path)

        if platform == 'win32':
            a = [item.split('\\')[-1].split('.')[-2] for item in items]
            b = [item.split('\\')[-1].split('.')[-2] for item in stabilized_items]
        if platform == 'darwin' or platform == 'linux':
            a = [item.split('/')[-1].split('.')[-2] for item in items]
            b = [item.split('/')[-1].split('.')[-2] for item in stabilized_items]

        return np.array(self.get_items_from_path(self.master.recorded_video_directory_path))[np.invert(np.in1d(a,b))]


    def get_items_from_path(self,path):
        # print(path+'/*.mp4')
        a =glob.glob(path+'/*.avi')
        a.extend(glob.glob(path + '/*.mp4'))
        try:
            for index,file_name in enumerate(a):
                os.rename(file_name,file_name.replace(',',''))
                a[index] = file_name.replace(',','')
        except:
            pass
        return a #needs to be updated if new formats are allowed

    def update(self):
        # print('here')
        # print(self.process)
        # print(self.process.current_stage)
        # print(self.master.selected_tab)
        # print('end here')

        if self.process is None:
            #self.master.selected_tab = 'analyze'

            # print('hello')
            # print(self.previously_selected_tab)
            self.master.selected_tab = self.previously_selected_tab
            self._unpack()
            self._destroy()
            self.top.destroy()
            self.destroy()



        else:
            self.iteration+=1

            self.process.update()
            try:
                self.information_label.config(text=str(self.iteration))
            except:
                pass

            if self.process.current_stage == 'finished':
                self.process = None
                self.master.options = None

            # self.t = 'updating'
            # self.information_label.config(text=self.t)

        # self.tab.update()
